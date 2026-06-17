# Final Review

## Attack Summary

The attacker flash-swapped AIC from the AIC/NEX Pancake pair, swapped AIC into DIP, manipulated the DIP/AIC pair with a fee-on-transfer deposit followed by `skim(PancakeRouter)` and `sync()`, then swapped remaining DIP back into AIC against the distorted reserves. After repaying the flash swap, the helper swapped residual AIC into USDC and sent the profit to `0x0d4024cd27538350a911d9b7ee90811fa4875ba3`.

## Root Cause

DIP's `_transfer` applies a 6% sell fee when the recipient is the DIP/AIC pair, but transfers involving the Pancake Router execute `super._transfer` inside the router branch and then fall through to a second `super._transfer`. The exploit combines those behaviors so `skim(PancakeRouter)` double-transfers the pair's excess DIP to the router, leaving only dust before `sync()` records a tiny DIP reserve and enables an outsized AIC withdrawal.

## Unresolved Good PoC Problems

None.
