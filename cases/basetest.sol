// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.15;

import "forge-std/Test.sol";

interface IERC20BalanceLog {
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
    function symbol() external view returns (string memory);
}

// Base contract for DeFi exploit PoCs. Inherit from this instead of Test directly.
// Provides before/after balance logging via the `balanceLog` modifier.
//
// Single-asset mode (default):
//   Set `fundingToken` to the token you profit in (address(0) = native ETH).
//   The `balanceLog` modifier logs that one token before and after testExploit().
//
// Multi-asset mode:
//   Set `multiAssetLog = true` and populate `fundingTokens[]` with every token to track.
//   The same `balanceLog` modifier logs all of them. No override needed.
//   Optionally set `attacker` to log a different address (e.g. a separate profit contract).
//   If `attacker` is left as address(0), it resolves to address(this).
contract BaseTestWithBalanceLog is Test {
    // Single-asset mode: the token to log profit in. address(0) = native ETH.
    address fundingToken = address(0);
    // Multi-asset mode: full list of tokens to track (ERC-20 or address(0) for native).
    address[] fundingTokens;
    // Set to true to enable multi-asset logging via fundingTokens[].
    bool multiAssetLog = false;
    // Address whose balances are logged. Defaults to address(this) when left as address(0).
    address attacker;

    function _tokenSymbol(address token) private view returns (string memory) {
        if (token == address(0)) return "ETH";
        try IERC20BalanceLog(token).symbol() returns (string memory symbol) {
            return symbol;
        } catch {
            return "TOKEN";
        }
    }

    function _tokenDecimals(address token) private view returns (uint8) {
        if (token == address(0)) return 18;
        try IERC20BalanceLog(token).decimals() returns (uint8 d) {
            return d;
        } catch {
            return 18;
        }
    }

    function _tokenBalance(address token, address account) private view returns (uint256) {
        if (token == address(0)) return account.balance;
        try IERC20BalanceLog(token).balanceOf(account) returns (uint256 balance) {
            return balance;
        } catch {
            return 0;
        }
    }

    function _attacker() private view returns (address) {
        return attacker == address(0) ? address(this) : attacker;
    }

    function logTokenBalance(address token, address account, string memory label) public {
        emit log_named_decimal_uint(
            string(abi.encodePacked(label, " ", _tokenSymbol(token), " Balance")),
            _tokenBalance(token, account),
            _tokenDecimals(token)
        );
    }

    function logMultipleTokenBalances(address[] memory tokens, address account, string memory label) internal {
        emit log_string(string(abi.encodePacked("=== ", label, " ===")));
        for (uint256 i = 0; i < tokens.length; i++) {
            logTokenBalance(tokens[i], account, "");
        }
    }

    modifier balanceLog() virtual {
        if (multiAssetLog) {
            _logMultiAssetBalances("Before exploit");
        } else {
            logTokenBalance(fundingToken, _attacker(), "Attacker Before exploit");
        }
        _;
        if (multiAssetLog) {
            _logMultiAssetBalances("After exploit");
        } else {
            logTokenBalance(fundingToken, _attacker(), "Attacker After exploit");
        }
    }

    modifier balanceLog2(address target) virtual {
        logTokenBalance(fundingToken, target, "Attacker Before exploit");
        _;
        logTokenBalance(fundingToken, target, "Attacker After exploit");
    }

    function _addFundingToken(address token) internal {
        fundingTokens.push(token);
    }

    function _addFundingTokens(address[] memory tokens) internal {
        for (uint256 i = 0; i < tokens.length; i++) {
            fundingTokens.push(tokens[i]);
        }
    }

    function _logMultiAssetBalances(string memory label) internal {
        logMultipleTokenBalances(fundingTokens, _attacker(), label);
    }
}
