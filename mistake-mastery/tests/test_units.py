"""图像处理、擦除接口适配器、坐标换算、装箱分页。"""

import base64
import json

import httpx
import numpy as np
import pytest

from app.adapters import imaging
from app.adapters.eraser import BaiduEraser, EraseError, TextInEraser, YoudaoEraser, find_image
from app.adapters.llm import parse_json
from app.services.printing import CONTENT_BOTTOM, CONTENT_H, CONTENT_TOP, Block, pack, split_landscape
from app.services.questions import bbox_to_pixels, content_hash
from tests.conftest import synthetic_page

PNG_1PX = imaging.encode_png_gray(np.full((4, 4), 255, np.uint8))


def test_perspective_detects_paper_and_flattens():
    img = imaging.decode(synthetic_page())
    t = imaging.detect_page_transform(img)
    assert t is not None
    assert 950 <= t["w"] <= 1050 and 1360 <= t["h"] <= 1470  # 纸张 1000×1414
    out = imaging.apply_transform(img, t)
    assert out.shape[:2] == (t["h"], t["w"])
    assert out[5:50, 5:50].mean() > 200  # 角上是白纸，不再是深色桌面


def test_colored_ink_removed_black_kept():
    img = imaging.apply_transform(imaging.decode(synthetic_page()), imaging.detect_page_transform(
        imaging.decode(synthetic_page())))
    gray = imaging.remove_colored_ink(img)
    b, g, r = (img[:, :, i].astype(int) for i in range(3))
    red = (r > 150) & (g < 90) & (b < 90)
    assert red.sum() > 500
    assert (gray[red] > 150).mean() > 0.95  # 红笔 ✗ 被擦掉
    black = (r < 60) & (g < 60) & (b < 60)
    assert (gray[black] < 100).mean() > 0.9  # 黑色印刷线条还在


def test_normalize_upload_limits_size():
    jpeg, w, h = imaging.normalize_upload(synthetic_page(3000, 4000))
    assert max(w, h) == imaging.MAX_SIDE and jpeg[:3] == b"\xff\xd8\xff"


@pytest.mark.parametrize("bbox,expect", [
    ([100, 200, 900, 500], [100.0, 400.0, 900.0, 1000.0]),  # 0–1000 归一化
    ([1100, 200, 1500, 1800], [1000.0, 200.0, 1000.0, 1800.0]),  # 像素坐标：超过宽度被裁到边界后宽度不足，退回整页
    (None, [0.0, 0.0, 1000.0, 2000.0]),
])
def test_bbox_to_pixels(bbox, expect):
    out = bbox_to_pixels(bbox, 1000, 2000)
    if expect == [1000.0, 200.0, 1000.0, 1800.0]:
        assert out == [0.0, 0.0, 1000.0, 2000.0]
    else:
        assert out == expect


def test_content_hash_ignores_spacing_and_punctuation():
    a = content_hash("math", "已知 $x=1$ ， 求 y 。", None)
    b = content_hash("math", "已知$x=1$,求y.", None)
    assert a == b
    assert a != content_hash("physics", "已知 $x=1$ ， 求 y 。", None)


def test_parse_json_handles_fences_and_chatter():
    assert parse_json('好的：\n```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('结果如下 {"items": [1, 2]} 以上') == {"items": [1, 2]}


def test_find_image_in_nested_json():
    b64 = base64.b64encode(PNG_1PX + b"\x00" * 300).decode()
    assert find_image({"result": {"image": b64}}).startswith(b"\x89PNG")
    assert find_image({"result": {"text": "x" * 400}}) is None


def _mock(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_baidu_token_then_erase():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        if req.url.path.endswith("/oauth/2.0/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert req.url.params["access_token"] == "tok"
        assert b"image=" in req.content
        return httpx.Response(200, json={"image_processed": base64.b64encode(PNG_1PX + b"\0" * 300).decode()})

    e = BaiduEraser("k", "s", "https://aip.baidubce.com/rest/2.0/ocr/v1/remove_handwriting", client=_mock(handler))
    assert e.erase(b"jpg").startswith(b"\x89PNG")
    assert e.erase(b"jpg").startswith(b"\x89PNG")
    assert calls.count("/oauth/2.0/token") == 1  # token 缓存


def test_youdao_signs_with_truncated_input():
    def handler(req: httpx.Request) -> httpx.Response:
        form = dict(httpx.QueryParams(req.content.decode()))
        q = form["q"]
        import hashlib
        trunc = q if len(q) <= 20 else q[:10] + str(len(q)) + q[-10:]
        expect = hashlib.sha256(("ak" + trunc + form["salt"] + form["curtime"] + "sec").encode()).hexdigest()
        assert form["sign"] == expect and form["signType"] == "v3"
        return httpx.Response(200, json={"errorCode": "0", "img": base64.b64encode(PNG_1PX + b"\0" * 300).decode()})

    assert YoudaoEraser("ak", "sec", "https://x/ocr", client=_mock(handler)).erase(b"x" * 100).startswith(b"\x89PNG")


def test_vendor_error_is_raised():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 40101, "message": "x-ti-app-id 不合法"})

    with pytest.raises(EraseError, match="40101"):
        TextInEraser("id", "sec", "https://x", client=_mock(handler)).erase(b"img")


def _block(seq: int, h_px: int, w_px: int = 1000, width_mm: float = 180.0) -> Block:
    return Block(seq, f"{seq}", np.zeros((h_px, w_px), np.uint8), width_mm)


def test_pack_never_splits_and_respects_bounds():
    blocks = [_block(i, h) for i, h in enumerate([300, 900, 500, 1400, 200, 3000], start=1)]
    pages = pack(blocks)
    seen = [pl.block.seq for page in pages for pl in page]
    assert seen == [1, 2, 3, 4, 5, 6]  # 顺序不变、不丢题
    for page in pages:
        for pl in page:
            assert pl.y >= CONTENT_TOP - 1e-6
            assert pl.y + pl.h <= CONTENT_BOTTOM + 1e-6
    tall = [pl for page in pages for pl in page if pl.block.seq == 6][0]
    assert tall.h <= CONTENT_H  # 超高的题等比缩小到一页


def test_split_landscape_halves_a3():
    halves = split_landscape(np.zeros((1000, 1500), np.uint8))
    assert len(halves) == 2 and halves[0].shape == (1000, 750)
    assert len(split_landscape(np.zeros((1400, 1000), np.uint8))) == 1


def test_json_roundtrip_of_curriculum_codes():
    from app.curriculum import load
    cur = load()
    assert json.loads(json.dumps(list(cur.kps)))
    assert cur.l1_of("P.EXP.INQ.LENS").code == "P.EXP"


def test_header_mask_only_first_page_and_only_when_enabled(tmp_path, make_settings):
    from types import SimpleNamespace

    from app.services.capture import _outbound
    img = np.zeros((100, 50, 3), np.uint8)
    on = SimpleNamespace(settings=make_settings(tmp_path, mask_header_ratio=0.1))
    off = SimpleNamespace(settings=make_settings(tmp_path))
    assert _outbound(on, img, 1)[:10].min() == 255 and _outbound(on, img, 1)[10:].max() == 0
    assert _outbound(on, img, 2).max() == 0  # 只处理第 1 页
    assert _outbound(off, img, 1).max() == 0  # 默认不涂


def test_parse_json_skips_reasoning_block():
    # 推理模型可能把思考过程放在 <think> 里，里面也可能有花括号
    assert parse_json('<think>设 {x} 为……</think>\n{"ok": true}') == {"ok": True}


def test_model_preset_and_mimo_endpoint(make_settings, tmp_path):
    from app.adapters.llm import LLMClient, default_models, resolve_preset
    from app.db import Database

    tmp_path.mkdir(exist_ok=True)
    s = make_settings(tmp_path, model_preset="mimo", mimo_api_key="tp-test")
    models = default_models(s)
    assert models["recognize"] == models["bank"] == models["solve"] == "mimo:mimo-v2.6-flash"  # 要看图
    assert models["lesson"] == "mimo:mimo-v2.6-pro"
    assert default_models(make_settings(tmp_path))["recognize"].startswith("qwen:")  # 默认还是通义千问
    # 没写 XT_MODEL_PRESET：只填了 MiMo 的密钥就用 MiMo，两家都填了用通义千问；写了就按写的
    assert resolve_preset(make_settings(tmp_path, mimo_api_key="tp-x"))[0] == "mimo"
    assert resolve_preset(make_settings(tmp_path, mimo_api_key="tp-x", dashscope_api_key="sk-x"))[0] == "qwen"
    assert resolve_preset(make_settings(tmp_path, mimo_api_key="tp-x", model_preset="qwen"))[0] == "qwen"
    assert resolve_preset(make_settings(tmp_path, model_preset="MiMo "))[0] == "mimo"
    assert "不认识" in resolve_preset(make_settings(tmp_path, model_preset="gpt"))[1]
    # DeepSeek：只填它就用它；和 MiMo 一起填时按顺序用 MiMo，写了 XT_MODEL_PRESET=deepseek 就用 DeepSeek
    ds = make_settings(tmp_path, deepseek_api_key="sk-d")
    assert resolve_preset(ds)[0] == "deepseek"
    assert set(default_models(ds).values()) == {"deepseek:deepseek-v4-flash", "doubao:"}
    assert resolve_preset(make_settings(tmp_path, deepseek_api_key="sk-d", mimo_api_key="tp-x"))[0] == "mimo"
    assert resolve_preset(make_settings(tmp_path, deepseek_api_key="sk-d", mimo_api_key="tp-x",
                                        model_preset="deepseek"))[0] == "deepseek"

    db = Database(s.data_dir / "t.db")
    llm = LLMClient(s, db, s.data_dir / "cache", models={"classify": "qwen:qwen-plus"})
    assert llm.model_for("bank") == ("mimo", "mimo-v2.6-flash")
    assert llm.model_for("classify") == ("qwen", "qwen-plus")  # 设置页里单独改过的仍然生效
    assert str(llm._client("mimo").base_url).startswith("https://token-plan-cn.xiaomimimo.com/v1")
    s2 = make_settings(tmp_path, model_preset="mimo", mimo_api_key="sk-x", mimo_base_url="https://api.example.com/v1")
    assert str(LLMClient(s2, db, s2.data_dir / "cache")._client("mimo").base_url).startswith("https://api.example.com/v1")
    assert str(LLMClient(ds, db, ds.data_dir / "cache")._client("deepseek").base_url).startswith(
        "https://api.deepseek.com/v1")
    db.dispose()


def test_bakeoff_key_report_and_unknown_env_names(make_settings, tmp_path, monkeypatch):
    from app.config import unknown_env_names
    from app.tools.bakeoff import key_report

    env = tmp_path / ".env"
    env.write_text("# 注释\nXT_DATA_DIR=/x\nxt_mimo_api_key=tp-1\nexport XT_ERASER=none\n"
                   "OPENAI_API_KEY=sk-1\nXT_MIMO_KEY=tp-2\n\nnot a line\n", encoding="utf-8")
    assert unknown_env_names(env) == ["OPENAI_API_KEY", "XT_MIMO_KEY"]
    assert unknown_env_names(tmp_path / "nope") == []

    monkeypatch.chdir(tmp_path)  # key_report 读当前目录下的 .env
    lines, usable = key_report(make_settings(tmp_path, mimo_api_key="tp-secret"))
    text = "\n".join(lines)
    assert usable and "小米 MiMo 已填（tp-…）" in text and "secret" not in text  # 不显示密钥
    assert "默认用 mimo" in text and "OPENAI_API_KEY 程序不认识" in text
    lines, usable = key_report(make_settings(tmp_path, mimo_api_key="tp-1", model_preset="qwen"))
    assert usable and "XT_MODEL_PRESET 改成 mimo" in lines[-1]
    lines, usable = key_report(make_settings(tmp_path))
    assert not usable and "还没有大模型密钥" in lines[-1]


def test_explain_api_errors():
    import httpx
    from openai import APIConnectionError, APIStatusError

    from app.adapters.llm import explain_error

    req = httpx.Request("POST", "https://example.com/v1/chat/completions")

    def status(code: int, body: str) -> APIStatusError:
        return APIStatusError(body, response=httpx.Response(code, request=req), body=None)

    quota = explain_error(status(429, "{'message': 'quota exhausted'}"), "mimo", "mimo-v2.6-flash")
    assert "额度用完了" in quota and "quota exhausted" in quota  # 原始报错也留着
    assert "限速" in explain_error(status(429, "too many requests"), "mimo", "m")
    assert "XT_MIMO_API_KEY" in explain_error(status(401, "invalid key"), "mimo", "m")
    assert "没有 mimo-x 这个模型" in explain_error(status(404, "not found"), "mimo", "mimo-x")
    assert "代理" in explain_error(APIConnectionError(request=req), "qwen", "m")
    assert explain_error(ValueError("怪"), "qwen", "m") == "qwen:m 调用失败：怪"
