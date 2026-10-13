"""运行配置：密钥和路径来自 .env，非敏感设置另存在数据仓库的 settings.json。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="XT_", extra="ignore")

    # 私有数据仓库的本地克隆。孩子的数据只写在这里，绝不写进代码仓库。
    data_dir: Path = Path("data")

    # 家庭密码：明文（XT_FAMILY_PASSWORD）或 scrypt 哈希（XT_FAMILY_PASSWORD_HASH，
    # 用 python -m app.tools.hash_password 生成）。两个都没设时，登录页会提示先配置。
    family_password: str = ""
    family_password_hash: str = ""

    # 大模型接口密钥（OpenAI 兼容协议）。
    dashscope_api_key: str = ""
    ark_api_key: str = ""
    deepseek_api_key: str = ""

    # 去手写接口：none | local_color | baidu | youdao | textin
    eraser: str = "local_color"
    baidu_api_key: str = ""
    baidu_secret_key: str = ""
    youdao_app_key: str = ""
    youdao_app_secret: str = ""
    textin_app_id: str = ""
    textin_secret_code: str = ""
    # 各家接口地址以控制台文档为准，可以在 .env 里覆盖。
    baidu_erase_url: str = "https://aip.baidubce.com/rest/2.0/ocr/v1/remove_handwriting"
    youdao_erase_url: str = "https://openapi.youdao.com/ocr_writing_erase"
    textin_erase_url: str = "https://api.textin.com/ai/service/v1/handwritten_erase"

    daily_cost_cap_cny: float = 5.0

    # 送给外部接口前，把第 1 页最上方这一比例的区域涂白（卷头的姓名、班级、学号）。
    # 默认 0 = 不涂：很多卷子第 1 题紧挨着卷头，一刀切容易把题目也涂掉。可以试着设成 0.08。
    mask_header_ratio: float = 0.0

    # 生成 PDF 用的 Chromium。留空时用 `playwright install chromium` 安装的那个。
    chromium_path: str = ""

    # GitHub 同步：最后一次改动后多少秒提交；是否推送。
    sync_enabled: bool = True
    sync_debounce_seconds: int = 120
    sync_push: bool = True

    # 测试时设为 True：后台任务同步执行，便于断言。
    jobs_inline: bool = False

    @property
    def local_dir(self) -> Path:
        """数据仓库内的本地目录（已被 .gitignore 排除）：SQLite、缓存、PDF。"""
        return self.data_dir / ".local"

    @property
    def db_path(self) -> Path:
        return self.local_dir / "app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
