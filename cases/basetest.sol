// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.15;

import "forge-std/Test.sol";

interface IERC20BalanceLog {
    function balanceOf(address account) external view returns (uint256);
    function decimals() external view returns (uint8);
    function symbol() external view returns (string memory);
}

contract BaseTestWithBalanceLog is Test {
    address fundingToken = address(0);

    function _tokenSymbol(address token) internal view returns (string memory) {
        if (token == address(0)) return "ETH";
        try IERC20BalanceLog(token).symbol() returns (string memory symbol) {
            return symbol;
        } catch {
            return "TOKEN";
        }
    }

    function _tokenDecimals(address token) internal view returns (uint8) {
        if (token == address(0)) return 18;
        try IERC20BalanceLog(token).decimals() returns (uint8 decimals) {
            return decimals;
        } catch {
            return 18;
        }
    }

    function _tokenBalance(address token, address account) internal view returns (uint256) {
        if (token == address(0)) return account.balance;
        try IERC20BalanceLog(token).balanceOf(account) returns (uint256 balance) {
            return balance;
        } catch {
            return 0;
        }
    }

    function logTokenBalance(address token, address account, string memory label) public {
        emit log_named_decimal_uint(
            string(abi.encodePacked(label, " ", _tokenSymbol(token), " Balance")),
            _tokenBalance(token, account),
            _tokenDecimals(token)
        );
    }

    modifier balanceLog() virtual {
        logTokenBalance(fundingToken, address(this), "Attacker Before exploit");
        _;
        logTokenBalance(fundingToken, address(this), "Attacker After exploit");
    }

    modifier balanceLog2(address target) virtual {
        logTokenBalance(fundingToken, target, "Attacker Before exploit");
        _;
        logTokenBalance(fundingToken, target, "Attacker After exploit");
    }
}
