from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from framework.api.client import BettingApiClient
from framework.api.models import Match, Selection
from framework.utils.money import expected_payout, to_money


@dataclass(frozen=True)
class StakeCase:
    stake: Any
    expected_status: int
    expected_error: str | None = None
    spend_before: Decimal | None = None


STAKE_CASES = [
    pytest.param(StakeCase(1.00, 200), id="min-boundary-1.00"),
    pytest.param(StakeCase(100.00, 200), id="max-boundary-100.00"),
    pytest.param(StakeCase(0.99, 422, "invalid_stake_min"), id="below-min-0.99"),
    pytest.param(StakeCase(0, 422, "invalid_stake_min"), id="zero"),
    pytest.param(
        StakeCase(-5, 422, "invalid_stake_min"),
        id="negative",
        marks=pytest.mark.xfail(
            reason="BUG-02: negative stake is accepted and credited to the balance", raises=AssertionError
        ),
    ),
    pytest.param(StakeCase(100.01, 422, "invalid_stake_max"), id="above-max-100.01"),
    pytest.param(StakeCase(10.123, 422, "invalid_stake_precision"), id="three-decimals"),
    pytest.param(StakeCase("abc", 422, "invalid_stake_type"), id="non-numeric"),
    pytest.param(
        StakeCase(50, 422, "insufficient_balance", spend_before=Decimal("100")),
        id="exceeds-balance",
        marks=pytest.mark.xfail(reason="BUG-01: API does not check the available balance", raises=AssertionError),
    ),
]


@pytest.mark.api
@pytest.mark.parametrize("case", STAKE_CASES)
def test_place_bet_enforces_stake_rules(
    api: BettingApiClient, upcoming_match: Match, starting_balance: Decimal, case: StakeCase
) -> None:
    """Stake limits and the balance check protect money, and the UI can be bypassed,
    so the API must enforce them (spec 4.1). Fast and stable, so it covers many boundaries."""
    selection = Selection.HOME
    if case.spend_before is not None:
        api.place_bet(upcoming_match.id, selection, float(case.spend_before)).raise_for_status()
    balance_before = api.fetch_balance()
    if case.expected_error == "insufficient_balance":
        assert to_money(case.stake) > balance_before, "precondition: stake must exceed the balance"

    response = api.place_bet(upcoming_match.id, selection, case.stake)

    assert response.status_code == case.expected_status, response.text
    body = response.json()
    if case.expected_status == 200:
        stake = to_money(case.stake)
        odds = to_money(upcoming_match.odds[selection])
        assert to_money(body["stake"]) == stake
        assert to_money(body["odds"]) == odds
        assert to_money(body["payout"]) == expected_payout(stake, odds)
        assert to_money(body["balance"]) == balance_before - stake
        assert api.fetch_balance() == balance_before - stake, "persisted balance must drop by the stake"
    else:
        assert body.get("error") == case.expected_error, response.text
        assert api.fetch_balance() == balance_before, "a rejected bet must not change the balance"
