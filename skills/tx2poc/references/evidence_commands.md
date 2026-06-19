# Evidence Commands

Use these only when the trace leaves an important gap.

## Calldata

```bash
python "$SKILL_DIR/scripts/decode_calldata.py" <0x_calldata>
```

## Function Selector

```bash
curl -s "https://www.4byte.directory/api/v1/signatures/?hex_signature=<0xselector>"
```

## Token Metadata

```bash
cast call <token> "symbol()(string)" --rpc-url <rpc_url_or_foundry_alias>
cast call <token> "name()(string)" --rpc-url <rpc_url_or_foundry_alias>
cast call <token> "decimals()(uint8)" --rpc-url <rpc_url_or_foundry_alias>
```

## State-Sensitive Address Probe

Use when attacker-controlled address state may matter, such as self-call, delegatecall/EIP-7702-like execution, custom credit/lock/epoch accounting, or balance/credit/allowance failures.

```bash
python "$SKILL_DIR/scripts/state_probe.py" \
  --chain <chain> \
  --block <fork_block> \
  --address <attacker_or_attack_contract> \
  --token <token_or_accounting_contract> \
  --spender <spender_if_allowance_matters> \
  --view <custom_view_name=0xselector_if_needed> \
  --contract <callee_or_helper_if_needed> \
  --address-view <custom_address_view_name=0xselector[:address|none]> \
  --markdown
```

Custom views are opt-in simple `uint view(address)` probes. Pass each custom selector explicitly, for example `--view creditOf=0x75807250`. Use `cast call` for protocol-specific state.

Address views are opt-in address-returning helper probes. The default argument kind is `address`, for example `--contract <helper> --address-view parent=0xf1f9d8c9` calls `parent(<address>)`. Use `:none` for no-arg views such as `owner()` or `admin()`, for example `--address-view owner=0x8da5cb5b:none`.

## Proxy Check

EIP-1967 implementation slot:

```bash
cast storage <address> 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc --rpc-url <rpc_url_or_foundry_alias>
```

Explorer source/metadata:

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<chainid>&module=contract&action=getsourcecode&address=<address>&apikey=$ETHERSCAN_API_KEY"
```
