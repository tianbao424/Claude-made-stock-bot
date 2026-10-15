"""启动：uv run python -m app（默认监听 0.0.0.0:8000，手机连同一个 Wi-Fi 即可访问）。"""

import argparse
import ipaddress
import logging
import socket
import subprocess
import sys
from pathlib import Path

import uvicorn

from app.config import get_settings

CODE_DIR = Path(__file__).resolve().parents[2]  # 代码仓库（Claude-made-stock-bot）
# 家里 Wi-Fi 的地址段。代理、VPN 软件的虚拟网卡常用 198.18.x.x、240.x.x.x 这类地址，手机连不上，不算。
HOME_NETS = [ipaddress.ip_network(n) for n in ("192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12")]


def _route_ip(probe: str) -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((probe, 80))  # 不会真的发包，只是借此拿到去往这个地址时用的本机地址
            return s.getsockname()[0]
    except OSError:
        return None


def home_ips(candidates: list[str]) -> list[str]:
    """只留家里局域网的地址，192.168 开头的排在前面，去重。"""
    out = []
    for ip in dict.fromkeys(c for c in candidates if c):
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if any(addr in net for net in HOME_NETS):
            out.append(ip)
    return sorted(out, key=lambda ip: not ip.startswith("192.168."))


def lan_ips() -> tuple[list[str], str | None]:
    """手机可以用的本机地址，以及按路由表拿到的地址（开着代理软件时可能是它的虚拟网卡）。"""
    routed = _route_ip("192.168.1.1")
    found = [routed] + [_route_ip(p) for p in ("10.0.0.1", "172.16.0.1")]
    try:
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    if sys.platform == "darwin":  # Mac：直接问 Wi-Fi 网卡
        for iface in ("en0", "en1"):
            try:
                r = subprocess.run(["ipconfig", "getifaddr", iface], capture_output=True, text=True, timeout=3)
                found.append(r.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                pass
    return home_ips([ip for ip in found if ip]), routed


def data_dir_problems(data_dir: Path, code_dir: Path = CODE_DIR) -> tuple[list[str], list[str]]:
    """启动前检查 XT_DATA_DIR：返回（必须先改的问题，提醒）。"""
    errors: list[str] = []
    warnings: list[str] = []
    text = str(data_dir)
    if "你的用户名" in text or not data_dir.is_absolute():
        errors.append(f"XT_DATA_DIR 还没改成实际位置（现在是 {text}）。打开 mistake-mastery 里的 .env，"
                      "改成数据仓库的完整路径，例如 /Users/zhangsan/xuetou-data（Windows 用正斜杠：C:/Users/zhangsan/xuetou-data）")
        return errors, warnings
    if not data_dir.exists():
        errors.append(f"找不到数据仓库文件夹 {text}。先 git clone 你的私有数据仓库，再把 .env 里的 XT_DATA_DIR 改成它的位置")
        return errors, warnings
    data, code = data_dir.resolve(), code_dir.resolve()
    if data == code or data.is_relative_to(code) or code.is_relative_to(data):
        errors.append(f"数据仓库（{data}）和程序（{code}）套在了一起。两个文件夹要并排放，"
                      "例如 ~/xuetou-data 和 ~/Claude-made-stock-bot")
    if not (data_dir / ".git").exists():
        warnings.append(f"{text} 不是 git clone 下来的数据仓库，数据不会同步到 GitHub")
    if "Mobile Documents" in text or "CloudStorage" in text:
        warnings.append("数据仓库放在 iCloud 等网盘里，可能产生冲突副本、损坏数据库。建议移到用户目录下，例如 ~/xuetou-data")
    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="学透（本地版）")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    errors, warnings = data_dir_problems(get_settings().data_dir)
    for w in warnings:
        print(f"\n  ⚠ {w}")
    if errors:
        for e in errors:
            print(f"\n  ✗ {e}")
        print("\n  改好 .env 后重新运行：uv run python -m app\n")
        raise SystemExit(1)

    ips, routed = lan_ips()
    print("\n  学透已启动")
    print(f"  · 这台电脑上打开：http://localhost:{args.port}")
    if ips:
        print(f"  · 手机连同一个 Wi-Fi 打开：http://{ips[0]}:{args.port}")
    else:
        print("  · 手机访问：在系统设置 → Wi-Fi → 详细信息里查看本机 IP 地址，打开 http://那个地址:"
              f"{args.port}")
    if routed and routed not in ips:
        print("  · 这台电脑好像开着代理或 VPN 软件：手机打不开的话，关掉它的“增强模式 / TUN 模式”再试")
    print()
    uvicorn.run("app.main:create_app", factory=True, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
