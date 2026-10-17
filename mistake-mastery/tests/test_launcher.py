"""启动前的检查：XT_DATA_DIR 没改、不存在、和程序套在一起、不是 git 仓库、放在 iCloud；.env 里拼错的名字、
还没填大模型密钥；手机访问地址。"""

from pathlib import Path

from app.__main__ import data_dir_problems, env_warnings, home_ips


def test_data_dir_placeholder_and_missing(tmp_path):
    errors, _ = data_dir_problems(Path("/Users/你的用户名/xuetou-data"), tmp_path / "code")
    assert errors and "还没改成实际位置" in errors[0]
    errors, _ = data_dir_problems(Path("data"), tmp_path / "code")  # 相对路径：没填
    assert errors and "还没改成实际位置" in errors[0]
    errors, _ = data_dir_problems(tmp_path / "nope", tmp_path / "code")
    assert errors and "找不到数据仓库文件夹" in errors[0]


def test_data_dir_nested_with_code_and_warnings(tmp_path):
    code = tmp_path / "Claude-made-stock-bot"
    (code / "mistake-mastery").mkdir(parents=True)
    # 程序被下载到了数据仓库里面
    data = tmp_path / "xuetou-data"
    (data / ".git").mkdir(parents=True)
    nested_code = data / "Claude-made-stock-bot"
    nested_code.mkdir()
    errors, _ = data_dir_problems(data, nested_code)
    assert errors and "套在了一起" in errors[0]
    # 数据仓库在程序里面
    inner = code / "xuetou-data"
    (inner / ".git").mkdir(parents=True)
    assert "套在了一起" in data_dir_problems(inner, code)[0][0]
    # 正常：并排放
    assert data_dir_problems(data, code) == ([], [])
    # 不是 git 仓库、放在 iCloud：只提醒，不拦着
    plain = tmp_path / "Mobile Documents" / "xuetou-data"
    plain.mkdir(parents=True)
    errors, warnings = data_dir_problems(plain, code)
    assert errors == [] and len(warnings) == 2


def test_home_ips_skip_vpn_addresses():
    found = ["240.0.0.1", "198.18.0.1", "127.0.0.1", "10.0.0.8", "192.168.1.23", "192.168.1.23", "", "bad"]
    assert home_ips(found) == ["192.168.1.23", "10.0.0.8"]
    assert home_ips(["240.0.0.1"]) == []


def test_env_warnings(tmp_path, make_settings):
    env = tmp_path / ".env"
    env.write_text("XT_MIMO_API_KEY=tp-1\nMIMO_API_KEY=tp-1\n", encoding="utf-8")
    warnings = env_warnings(make_settings(tmp_path, mimo_api_key="tp-1"), env)
    assert len(warnings) == 1 and "MIMO_API_KEY 程序不认识" in warnings[0]
    warnings = env_warnings(make_settings(tmp_path), tmp_path / "nope")
    assert len(warnings) == 1 and "还没填大模型密钥" in warnings[0]
