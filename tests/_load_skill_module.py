from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]
TX2POC_SCRIPTS = REPO_ROOT / ".agents" / "skills" / "tx2poc" / "scripts"


def load_tx2poc_script(name: str) -> ModuleType:
    path = TX2POC_SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"tx2poc_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TX2POC_SCRIPTS))
    spec.loader.exec_module(module)
    return module
