# Evidence Commands

Use these only when the trace leaves an important gap.

## Calldata

```bash
python scripts/decode_calldata.py <0x_calldata>
```

## Function Selector

```bash
curl -s "https://www.4byte.directory/api/v1/signatures/?hex_signature=<0xselector>"
```

## Token Metadata

```bash
cast call <token> "symbol()(string)" --rpc-url <chain>
cast call <token> "name()(string)" --rpc-url <chain>
cast call <token> "decimals()(uint8)" --rpc-url <chain>
```

## State-Sensitive Address Probe

Use when attacker-controlled address state may matter, such as self-call, delegatecall/EIP-7702-like execution, custom credit/lock/epoch accounting, or balance/credit/allowance failures.

```bash
python scripts/state_probe.py \
  --chain <chain> \
  --block <fork_block> \
  --address <attacker_or_attack_contract> \
  --token <token_or_accounting_contract> \
  --spender <spender_if_allowance_matters> \
  --view <custom_view_if_needed> \
  --markdown
```

Custom views are opt-in. Supported simple `uint view(address)` probes: `creditOf`, `creditlessOf`, `lockedOf`, `debtOf`. Use `cast call` for protocol-specific state.

## Proxy Check

EIP-1967 implementation slot:

```bash
cast storage <address> 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc --rpc-url <chain>
```

Explorer source/metadata:

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=<chainid>&module=contract&action=getsourcecode&address=<address>&apikey=$ETHERSCAN_API_KEY"
```
