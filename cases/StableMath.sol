// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity ^0.8.0;

library StableMath {
    using FixedPoint for uint256;

    uint256 internal constant AMP_PRECISION = 1e3;

    function _calculateInvariant(
        uint256 amplificationParameter,
        uint256[] memory balances
    ) internal pure returns (uint256) {
        return calculateInvariant(amplificationParameter, balances);
    }

    function calculateInvariant(
        uint256 amplificationParameter,
        uint256[] memory balances
    ) internal pure returns (uint256) {
        uint256 sum;
        uint256 numTokens = balances.length;
        for (uint256 i; i < numTokens; ++i) {
            sum += balances[i];
        }
        if (sum == 0) return 0;

        uint256 invariant = sum;
        uint256 ampTimesTotal = amplificationParameter * numTokens;
        for (uint256 i; i < 255; ++i) {
            uint256 dP = invariant;
            for (uint256 j; j < numTokens; ++j) {
                dP = Math.divDown(Math.mul(dP, invariant), Math.mul(balances[j], numTokens));
            }

            uint256 prevInvariant = invariant;
            invariant = Math.divDown(
                Math.mul(
                    (Math.divDown(Math.mul(ampTimesTotal, sum), AMP_PRECISION) + Math.mul(dP, numTokens)), invariant
                ),
                Math.divDown(Math.mul((ampTimesTotal - AMP_PRECISION), invariant), AMP_PRECISION)
                    + Math.mul((numTokens + 1), dP)
            );

            if (invariant > prevInvariant) {
                if (invariant - prevInvariant <= 1) return invariant;
            } else if (prevInvariant - invariant <= 1) {
                return invariant;
            }
        }
        revert("stable invariant did not converge");
    }

    function _calcInGivenOut(
        uint256 amplificationParameter,
        uint256[] memory balances,
        uint256 tokenIndexIn,
        uint256 tokenIndexOut,
        uint256 tokenAmountOut,
        uint256 invariant
    ) internal pure returns (uint256) {
        return calcInGivenOut(amplificationParameter, balances, tokenIndexIn, tokenIndexOut, tokenAmountOut, invariant);
    }

    function calcInGivenOut(
        uint256 amplificationParameter,
        uint256[] memory balances,
        uint256 tokenIndexIn,
        uint256 tokenIndexOut,
        uint256 tokenAmountOut,
        uint256 invariant
    ) internal pure returns (uint256) {
        balances[tokenIndexOut] -= tokenAmountOut;
        uint256 finalBalanceIn =
            getTokenBalanceGivenInvariantAndAllOtherBalances(amplificationParameter, balances, invariant, tokenIndexIn);
        balances[tokenIndexOut] += tokenAmountOut;
        return finalBalanceIn - balances[tokenIndexIn] + 1;
    }

    function getTokenBalanceGivenInvariantAndAllOtherBalances(
        uint256 amplificationParameter,
        uint256[] memory balances,
        uint256 invariant,
        uint256 tokenIndex
    ) internal pure returns (uint256) {
        uint256 ampTimesTotal = amplificationParameter * balances.length;
        uint256 sum = balances[0];
        uint256 pD = balances[0] * balances.length;
        for (uint256 j = 1; j < balances.length; ++j) {
            pD = Math.divDown(Math.mul(Math.mul(pD, balances[j]), balances.length), invariant);
            sum += balances[j];
        }
        sum -= balances[tokenIndex];

        uint256 inv2 = Math.mul(invariant, invariant);
        uint256 c =
            Math.mul(Math.mul(Math.divUp(inv2, Math.mul(ampTimesTotal, pD)), AMP_PRECISION), balances[tokenIndex]);
        uint256 b = sum + Math.mul(Math.divDown(invariant, ampTimesTotal), AMP_PRECISION);
        uint256 tokenBalance = Math.divUp(inv2 + c, invariant + b);

        for (uint256 i; i < 255; ++i) {
            uint256 prevTokenBalance = tokenBalance;
            tokenBalance =
                Math.divUp(Math.mul(tokenBalance, tokenBalance) + c, Math.mul(tokenBalance, 2) + b - invariant);

            if (tokenBalance > prevTokenBalance) {
                if (tokenBalance - prevTokenBalance <= 1) return tokenBalance;
            } else if (prevTokenBalance - tokenBalance <= 1) {
                return tokenBalance;
            }
        }
        revert("stable balance did not converge");
    }
}

library FixedPoint {
    uint256 internal constant ONE = 1e18;

    function mulDown(uint256 a, uint256 b) internal pure returns (uint256) {
        return (a * b) / ONE;
    }

    function divUp(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a == 0) return 0;
        return ((a * ONE) - 1) / b + 1;
    }
}

library Math {
    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        return a * b;
    }

    function divDown(uint256 a, uint256 b) internal pure returns (uint256) {
        return a / b;
    }

    function divUp(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a == 0) return 0;
        return (a - 1) / b + 1;
    }
}
