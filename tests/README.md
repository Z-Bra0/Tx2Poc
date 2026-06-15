# tx2poc Tests

Root `tests/` covers lightweight Python/tooling behavior for tx2poc scripts.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests -q
```

Keep these tests offline and deterministic. Generated Foundry PoCs stay under root `cases/`.
