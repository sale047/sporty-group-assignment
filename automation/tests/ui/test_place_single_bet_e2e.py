import re
from decimal import Decimal

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from framework.api.client import BettingApiClient
from framework.api.models import Match, Selection
from framework.ui.components.bet_slip import SlipSelection
from framework.ui.pages.betting_page import BettingPage
from framework.utils.money import expected_payout, to_money
from framework.utils.soft_assert import SoftAssertions

BET_ID_PATTERN = re.compile(r"#?B-\d+")


@pytest.mark.ui
def test_place_single_bet_end_to_end(
    driver: WebDriver,
    settings: Settings,
    api: BettingApiClient,
    upcoming_match: Match,
    starting_balance: Decimal,
) -> None:
    """Core revenue journey: slip, receipt and balance must match what the backend recorded.
    Only an E2E test can catch the UI showing different values than the API stored."""
    selection = Selection.HOME
    stake = "10"
    odds = to_money(upcoming_match.odds[selection])
    payout = expected_payout(stake, odds)
    balance_after = starting_balance - to_money(stake)

    page = BettingPage(driver, settings.ui_timeout).open(settings.base_url, settings.user_id)
    assert page.header_balance() == starting_balance, "header must show the persisted balance on load"

    slip = page.select_odds(upcoming_match.id, selection)
    slip.enter_stake(stake)
    assert slip.selection() == SlipSelection(match=upcoming_match.label, market="Match Winner: Home", odds=odds)
    assert slip.total_stake() == to_money(stake)
    assert slip.potential_payout() == payout

    slip.place_bet()
    slip.wait_until_placing()
    place_bet_locked_while_placing = not slip.is_place_bet_enabled()
    receipt_modal = page.wait_for_receipt()
    receipt = receipt_modal.read()

    checks = SoftAssertions()
    checks.true(place_bet_locked_while_placing, "Place Bet must be disabled while 'Placing...' (spec 2.3)")
    checks.true(bool(BET_ID_PATTERN.fullmatch(receipt.bet_id)), f"receipt Bet ID looks invalid: {receipt.bet_id!r}")
    checks.equal(receipt.match, upcoming_match.label, "receipt match (home team first)")
    checks.true("match winner: home" in receipt.full_text.lower(), "receipt must show the selection (spec 2.4)")
    checks.equal(receipt.stake, to_money(stake), "receipt stake")
    checks.equal(receipt.odds, odds, "receipt odds at placement")
    checks.equal(receipt.payout, payout, "receipt potential payout (stake x odds)")
    checks.true(bool(receipt.placed_at), "receipt must show the placement timestamp")
    checks.equal(api.fetch_balance(), balance_after, "persisted balance after placement")

    receipt_modal.close()
    checks.equal(page.header_balance(), balance_after, "header balance after placement")
    checks.true(page.bet_slip.is_empty(), "bet slip must be cleared after closing the receipt")
    checks.assert_all()
