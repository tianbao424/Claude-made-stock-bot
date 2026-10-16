"""大模型客户端：OpenAI 兼容协议，按任务选模型，记录调用和费用，执行每日费用上限。"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI
from sqlalchemy import func

from app.config import Settings
from app.db import Database
from app.ids import today_str
from app.models import AiCall

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Provider:
    base_url: str
    key_attr: str  # Settings 上的密钥字段名
    base_attr: str | None = None  # Settings 上可以覆盖接口地址的字段名


PROVIDERS: dict[str, Provider] = {
    "qwen": Provider("https://dashscope.aliyuncs.com/compatible-mode/v1", "dashscope_api_key"),
    "doubao": Provider("https://ark.cn-beijing.volces.com/api/v3", "ark_api_key"),
    "deepseek": Provider("https://api.deepseek.com", "deepseek_api_key"),
    # 小米 MiMo：默认是 Token Plan（中国区）的地址；按量付费的账号在 .env 里改 XT_MIMO_BASE_URL
    "mimo": Provider("https://token-plan-cn.xiaomimimo.com/v1", "mimo_api_key", "mimo_base_url"),
}

# 每个任务默认用哪个模型（"平台:模型名"），可以在数据仓库的 settings.json 里覆盖。
# 型号以各平台控制台为准，见 docs/05-ai-design.md §2。
DEFAULT_MODELS: dict[str, str] = {
    "recognize": "qwen:qwen3-vl-plus",
    "bank": "qwen:qwen3-vl-plus",  # 题库导入：印刷卷子的切题和答案页
    "classify": "qwen:qwen-plus",
    "solve": "qwen:qwen3-vl-plus",
    "verify": "doubao:",  # 交叉校验要换一家；v0.2 起使用，填上豆包的模型名
    "tutor": "qwen:qwen-plus",
    "lesson": "qwen:qwen-max",  # 知识点讲解：要讲对、讲清楚，用更强的模型（一份约 ¥0.03）
}

# 一键换一家：各任务的默认模型换成下面哪一套，见 resolve_preset。
# 要看图的任务（识别切题、题库导入、解答）用能看图的 mimo-v2.5；纯文字的讲解用推理更强的 mimo-v2.5-pro。
# 设置页里单独改过的任务仍以设置页为准。
PRESETS: dict[str, dict[str, str]] = {
    "qwen": DEFAULT_MODELS,
    "mimo": {
        "recognize": "mimo:mimo-v2.5",
        "bank": "mimo:mimo-v2.5",
        "classify": "mimo:mimo-v2.5",
        "solve": "mimo:mimo-v2.5",
        "verify": "doubao:",  # 交叉校验要换一家
        "tutor": "mimo:mimo-v2.5-pro",
        "lesson": "mimo:mimo-v2.5-pro",
    },
}


# 每套默认模型要哪家的密钥：（Settings 上的字段，.env 里的名字，叫什么）
PRESET_KEYS: dict[str, tuple[str, str, str]] = {
    "qwen": ("dashscope_api_key", "XT_DASHSCOPE_API_KEY", "通义千问"),
    "mimo": ("mimo_api_key", "XT_MIMO_API_KEY", "小米 MiMo"),
}


def resolve_preset(settings: Settings) -> tuple[str, str]:
    """（用哪套默认模型，为什么）。.env 里写了 XT_MODEL_PRESET 就按它；没写时看填了哪家的密钥：
    填了通义千问的用通义千问，只填了小米 MiMo 的用 MiMo。"""
    chosen = (settings.model_preset or "").strip().lower()
    if chosen in PRESETS:
        return chosen, f"XT_MODEL_PRESET={chosen}"
    if chosen:
        return "qwen", f"XT_MODEL_PRESET={chosen} 不认识（只能是 {' 或 '.join(PRESETS)}），先用 qwen"
    if not settings.dashscope_api_key.strip() and settings.mimo_api_key.strip():
        return "mimo", "只填了小米 MiMo 的密钥，自动用 MiMo"
    return "qwen", "默认"


def default_models(settings: Settings) -> dict[str, str]:
    return dict(PRESETS[resolve_preset(settings)[0]])

# 估算费用用的单价（元/百万 tokens，输入/输出），只用于费用上限和统计，以账单为准。
PRICES: dict[str, tuple[float, float]] = {
    "qwen3-vl-plus": (1.0, 10.0),
    "qwen3-vl-flash": (0.15, 1.5),
    "qwen-plus": (0.8, 2.0),
    "qwen-max": (2.4, 9.6),
}
DEFAULT_PRICE = (2.0, 10.0)


class CostCapExceeded(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


def image_part(data_url: str) -> dict:
    return {"type": "image_url", "image_url": {"url": data_url}}


def parse_json(text: str) -> Any:
    """从模型输出里取出 JSON：去掉推理模型的 <think> 段和 ``` 代码块标记，找第一个完整的对象或数组。"""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(text)


FakeHandler = Callable[[str, list[dict]], Any]


class LLMClient:
    def __init__(self, settings: Settings, db: Database, cache_dir: Path, models: dict[str, str] | None = None):
        self.settings = settings
        self.db = db
        self.cache_dir = cache_dir / "llm"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.defaults = default_models(settings)
        self.models = {**self.defaults, **(models or {})}
        self.fake: FakeHandler | None = None  # 测试或演示时注入，不调用真实接口
        self._clients: dict[str, OpenAI] = {}

    # ------------------------------------------------------------ 公共接口

    def chat_json(self, task: str, messages: list[dict], *, prompt_version: str,
                  temperature: float = 0.1, timeout: float = 180, fresh: bool = False) -> Any:
        """调用模型并解析 JSON 输出；解析失败时提醒模型重来一次。fresh：不用缓存（"重新生成"）。"""
        text = self._chat(task, messages, prompt_version=prompt_version, temperature=temperature, timeout=timeout,
                          fresh=fresh)
        try:
            return parse_json(text)
        except (json.JSONDecodeError, ValueError):
            retry = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": "上面的输出不是合法的 JSON。请只输出符合要求的 JSON，不要任何其他文字。"},
            ]
            text = self._chat(task, retry, prompt_version=prompt_version, temperature=0, timeout=timeout)
            try:
                return parse_json(text)
            except (json.JSONDecodeError, ValueError) as exc:
                raise LLMError(f"模型输出无法解析为 JSON：{text[:200]}") from exc

    def spent_today(self) -> float:
        with self.db.session() as s:
            total = s.query(func.coalesce(func.sum(AiCall.cost_cny), 0.0)).filter(
                AiCall.created_at.like(f"{today_str()}%")).scalar()
        return float(total or 0.0)

    def model_for(self, task: str) -> tuple[str, str]:
        spec = self.models.get(task) or self.defaults[task]
        provider, _, model = spec.partition(":")
        if not model:
            raise LLMError(f"任务 {task} 还没有配置模型（设置里填写“平台:模型名”）")
        return provider, model

    # ------------------------------------------------------------ 内部实现

    def _client(self, provider: str) -> OpenAI:
        if provider not in self._clients:
            p = PROVIDERS.get(provider)
            if p is None:
                raise LLMError(f"未知的模型平台：{provider}")
            key = getattr(self.settings, p.key_attr)
            if not key:
                raise LLMError(f"缺少 {provider} 的接口密钥（.env 里的 XT_{p.key_attr.upper()}）")
            base = (getattr(self.settings, p.base_attr) if p.base_attr else "") or p.base_url
            self._clients[provider] = OpenAI(api_key=key, base_url=base, max_retries=2)
        return self._clients[provider]

    def _cache_key(self, model: str, prompt_version: str, messages: list[dict]) -> str:
        raw = json.dumps([model, prompt_version, messages], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _chat(self, task: str, messages: list[dict], *, prompt_version: str, temperature: float,
              timeout: float, fresh: bool = False) -> str:
        if self.fake is not None:
            out = self.fake(task, messages)
            self._log(task, "fake", prompt_version, 0, 0, 0.0, 0, "ok")
            return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)

        provider, model = self.model_for(task)
        key = self._cache_key(model, prompt_version, messages)
        cached = self.cache_dir / f"{key}.txt"
        if cached.exists() and not fresh:
            return cached.read_text(encoding="utf-8")

        cap = self.settings.daily_cost_cap_cny
        if cap > 0 and self.spent_today() >= cap:
            raise CostCapExceeded(f"今天的 AI 费用已达到上限 ¥{cap:.2f}，明天自动恢复（可在 .env 调整 XT_DAILY_COST_CAP_CNY）")

        started = time.monotonic()
        try:
            resp = self._client(provider).chat.completions.create(
                model=model, messages=messages, temperature=temperature, timeout=timeout)
        except Exception as exc:
            self._log(task, model, prompt_version, 0, 0, 0.0, int((time.monotonic() - started) * 1000), "failed")
            raise LLMError(f"{provider}:{model} 调用失败：{exc}") from exc
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        pin, pout = PRICES.get(model, DEFAULT_PRICE)
        cost = (tin * pin + tout * pout) / 1_000_000
        self._log(task, model, prompt_version, tin, tout, cost, int((time.monotonic() - started) * 1000), "ok")
        cached.write_text(text, encoding="utf-8")
        return text

    def _log(self, task: str, model: str, version: str, tin: int, tout: int, cost: float, ms: int,
             outcome: str) -> None:
        with self.db.session() as s:
            s.add(AiCall(task=task, model=model, prompt_version=version, input_tokens=tin, output_tokens=tout,
                         cost_cny=round(cost, 5), latency_ms=ms, outcome=outcome))
