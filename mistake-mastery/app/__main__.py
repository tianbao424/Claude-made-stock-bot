"""启动：uv run python -m app（默认监听 0.0.0.0:8000，手机连同一个 Wi-Fi 即可访问）。"""

import argparse
import logging
import socket

import uvicorn


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.1.1", 80))  # 不会真的发包，只是借此拿到本机的局域网地址
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="学透（本地版）")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(f"\n  学透已启动：手机连上同一个 Wi-Fi，用浏览器打开  http://{lan_ip()}:{args.port}\n")
    uvicorn.run("app.main:create_app", factory=True, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
