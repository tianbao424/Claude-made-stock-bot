"""
扩展示例：CNN 恐惧贪婪指数 + 钉钉机器人推送

把这两个函数拷贝到 market_sentiment_monitor.py 的对应位置即可启用。
"""

import requests
from datetime import datetime


def cnn_fear_greed():
    """从 CNN 官方 JSON 端点拉取恐惧贪婪指数。"""
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    score = data["fear_and_greed"]["score"]
    rating = data["fear_and_greed"]["rating"]
    prev = data["fear_and_greed"]["previous_close"]

    if score >= 75:
        status, note = "hot", f"极度贪婪 (上次{prev:.0f})"
    elif score >= 55:
        status, note = "warm", f"贪婪 (上次{prev:.0f})"
    elif score <= 25:
        status, note = "cool", f"极度恐慌，反向机会 (上次{prev:.0f})"
    else:
        status, note = "neutral", f"中性 ({rating})"

    return {
        "name": "CNN 恐惧贪婪指数",
        "value": round(score, 1),
        "unit": "/100",
        "layer": "上层",
        "market": "US",
        "historical_context": f"上次{prev:.0f}, 趋势 {rating}",
        "status": status,
        "note": note,
    }


def send_dingtalk(webhook_url: str, body_md: str, secret: str = None):
    """
    钉钉机器人推送。

    1. 在钉钉群里添加一个"自定义机器人"
    2. 安全设置选"加签"（拿到 secret）或"关键词"
    3. 复制 webhook url
    """
    import time
    import hmac
    import hashlib
    import base64
    import urllib.parse

    url = webhook_url
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"市场情绪周报 {datetime.now():%m-%d}",
            "text": body_md[:4000],
        },
    }
    r = requests.post(url, json=payload, timeout=10)
    return r.status_code == 200


def send_wecom(webhook_url: str, body_md: str):
    """企业微信群机器人。"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": body_md[:4000],
        },
    }
    r = requests.post(webhook_url, json=payload, timeout=10)
    return r.status_code == 200


def send_telegram(bot_token: str, chat_id: str, body_md: str):
    """Telegram Bot 推送。"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": body_md[:4000],
        "parse_mode": "Markdown",
    }
    r = requests.post(url, json=payload, timeout=10)
    return r.status_code == 200


if __name__ == "__main__":
    print("CNN 恐惧贪婪指数测试：")
    try:
        result = cnn_fear_greed()
        print(result)
    except Exception as e:
        print(f"失败：{e}")
