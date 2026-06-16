from __future__ import annotations

from collections.abc import Mapping
import os

REQUIRED_ENV_VARS = ("ALCHEMY_API_KEY", "ETHERSCAN_API_KEY")


def missing_env_vars(environ: Mapping[str, str] | None = None) -> list[str]:
    env = os.environ if environ is None else environ
    return [name for name in REQUIRED_ENV_VARS if not env.get(name)]


def check_env(environ: Mapping[str, str] | None = None) -> None:
    missing = missing_env_vars(environ)
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")


def main() -> int:
    check_env()
    print("Environment preflight ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
