// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.10;

import "../basetest.sol";

// @KeyInfo - Total Lost : {number unit}
// Attacker : {0x00000000000000000000000000000000cafebabe}
// Attack Contract : {0x00000000000000000000000000000000deadbeef}
// Vulnerable Contract : {0x00000000000000000000000000000000baddcafe}
// Attack Tx : {link: https://skylens.certik.com/tx/eth/0x123456789}

// @Info
// Vulnerable Contract Code : {https://etherscan.io/address/0x00000000000000000000000000000000baddcafe#code}

// @Analysis
// Twitter Guy : {https://x.com/1nf0s3cpt/status/1583011233363824640}
//
// {Attack Summary}

address constant ATTACKER = 0x00000000000000000000000000000000cafebabe;
address constant ATTACK_CONTRACT = 0x00000000000000000000000000000000deadbeef;
address constant VULNERABLE_CONTRACT = 0x00000000000000000000000000000000baddcafe;
// Proxy/delegatecall cases: add ENTRY_STATE_CONTRACT and CODE_TARGET or IMPLEMENTATION constants.
// Call the entry/state address seen in the trace; use the implementation for source links and labels.

interface IVulnerableContract {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract ContractTest is BaseTestWithBalanceLog {
    function setUp() public {
        vm.createSelectFork("mainnet", 15460093);
        vm.label(ATTACKER, "Attacker");
        vm.label(ATTACK_CONTRACT, "Attack Contract");
        vm.label(VULNERABLE_CONTRACT, "Vulnerable Contract");
    }
    
    function testExploit() public {
        vm.startPrank(ATTACKER);
        vm.stopPrank();
    }
}
