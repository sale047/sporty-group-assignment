"""Money helpers. Amounts are compared as Decimal to avoid float rounding noise."""

import re
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")
_AMOUNT_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def to_money(value: float | int | str | Decimal) -> Decimal:
    """Normalise a number to a 2-decimal Decimal (str() keeps 2.45 from becoming 2.4500000000000001776)."""
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def parse_money(text: str) -> Decimal:
    """Extract the amount from UI text such as 'Balance: €125.50' or '€-10.00'."""
    match = _AMOUNT_PATTERN.search(text.replace(",", ""))
    if match is None:
        raise ValueError(f"No amount found in {text!r}")
    return to_money(match.group())


def expected_payout(stake: float | int | str | Decimal, odds: float | int | str | Decimal) -> Decimal:
    return to_money(Decimal(str(stake)) * Decimal(str(odds)))
