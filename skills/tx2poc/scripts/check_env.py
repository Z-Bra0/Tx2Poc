from __future__ import annotations

from collections.abc import Mapping
import os

REQUIRED_ENV_VARS = ("ETHERSCAN_API_KEY",)
OPTIONAL_ENV_VARS = ("ALCHEMY_API_KEY",)


def missing_env_vars(environ: Mapping[str, str] | None = None) -> list[str]:
    env = os.environ if environ is None else environ
    return [name for name in REQUIRED_ENV_VARS if not env.get(name)]


def trace_source(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return "alchemy" if env.get("ALCHEMY_API_KEY") else "blockscout (keyless)"


def check_env(environ: Mapping[str, str] | None = None) -> None:
    missing = missing_env_vars(environ)
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")


def main() -> int:
    check_env()
    print(f"Environment preflight ok. Trace source: {trace_source()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
