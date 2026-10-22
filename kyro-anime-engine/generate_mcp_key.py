#!/usr/bin/env python3
"""Generate a strong KAE MCP bearer token locally.

This script generates a secret only when you run it. Never commit the
generated token, paste it into chat, or put it in source code.
"""

import secrets


def main() -> None:
    # 64 random bytes = 512 bits of entropy, represented as 128 hex characters.
    print(secrets.token_hex(64))


if __name__ == "__main__":
    main()
