"""生成家庭密码的哈希：uv run python -m app.tools.hash_password，把输出填到 .env 的 XT_FAMILY_PASSWORD_HASH。"""

import getpass

from app.auth import hash_password


def main() -> None:
    pw = getpass.getpass("家庭密码（至少 12 位）：")
    if len(pw) < 12:
        raise SystemExit("太短了，至少 12 位")
    if pw != getpass.getpass("再输一遍："):
        raise SystemExit("两次输入不一致")
    print(f"XT_FAMILY_PASSWORD_HASH={hash_password(pw)}")


if __name__ == "__main__":
    main()
