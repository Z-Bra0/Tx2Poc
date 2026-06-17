# DIP Exploit Analysis

Transaction `0x1c09395848a87069c9d6ddbe5adc6249510aba7a2a83479a74b4280cafb5fb29` is a BNB Smart Chain transaction at block `104598279`. The sender `0x0d4024cd27538350a911d9b7ee90811fa4875ba3` calls verified attack contract `0xddef10a85a5c67a9af8398d297aa51f8716383c7` with `test(address,address,address,address)`, passing AIC, DIP, the AIC/NEX Pancake pair, and the AIC/DIP Pancake pair.

Twitter Guy : https://x.com/TenArmorAlert/status/2067059314519417163

The attack contract flash-swaps `19,000,000 AIC` from the AIC/NEX pair `0xf8331a897c5f32b57eab394af8adf0d00003cae1`. Inside `pancakeCall`, it swaps the borrowed AIC to DIP through Pancake Router and the AIC/DIP pair `0xf7d8267d01d1104da2dd30828aa9c0e1647919ef`.

The vulnerable contract is the verified DIP token at `0x6c60bf5db0670ae94489d3dde2c60f271625db50`. Its `_transfer` marks transfers to the DIP/AIC pair as sells and applies a `6%` fee. For transfers involving the Pancake Router, it calls `super._transfer(from, to, amount)` inside the `isRouter` branch but then falls through and calls `super._transfer(from, to, amount)` a second time.

The exploit uses those two behaviors together. After the first AIC-to-DIP swap, it transfers enough DIP into the DIP/AIC pair so the pair's apparent DIP balance is almost twice its recorded reserve after the 6% sell fee. It then calls `skim(PancakeRouter)`. Because the skim recipient is the router, DIP executes the pair-to-router transfer twice, draining nearly all of the pair's DIP balance. The attacker calls `sync()`, causing the pair to record a tiny DIP reserve with a large AIC reserve.

With the pair reserves distorted, the attack contract swaps its remaining DIP back to AIC and receives almost all AIC in the DIP/AIC pair. It repays the AIC/NEX flash swap and keeps the residual AIC. The final top-level call swaps the residual AIC through the AIC/USDC pair `0x473715a3ad10e6ea8e8d549cc0c0b1059b2ba9bd`, sending `111,097.596667856001191208 USDC` to the transaction sender.

The PoC uses a fresh local helper because the trace and verified source do not show attacker address-specific state. It preserves the observed flash-swap order, DIP balance manipulation, `skim`, `sync`, reverse swap, flash repayment, and final USDC forwarding to the real attacker address.
