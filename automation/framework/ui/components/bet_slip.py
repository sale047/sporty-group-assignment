from dataclasses import dataclass
from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from framework.ui.pages.base_page import BasePage
from framework.utils.money import parse_money


@dataclass(frozen=True)
class SlipSelection:
    match: str
    market: str
    odds: Decimal


class BetSlip(BasePage):
    ROOT = (By.ID, "bet-slip")
    EMPTY_STATE = (By.CSS_SELECTOR, "#bet-slip .betSlipBodyEmpty")
    SELECTION_TEAMS = (By.CSS_SELECTOR, "#bet-slip .betSelectionTeams")
    SELECTION_MARKET = (By.CSS_SELECTOR, "#bet-slip .betSelectionMarket")
    SELECTION_ODDS = (By.CSS_SELECTOR, "#bet-slip .betSelectionOdds")
    STAKE_INPUT = (By.ID, "bet-slip-stake-input")
    STAKE_WARNING = (By.CSS_SELECTOR, "#bet-slip .stakeWarning")
    TOTAL_STAKE = (By.ID, "bet-slip-total-stake")
    POTENTIAL_PAYOUT = (By.ID, "bet-slip-potential-payout")
    PLACE_BET = (By.ID, "bet-slip-place-bet")

    PLACING_LABEL = "placing..."

    def wait_until_has_selection(self) -> "BetSlip":
        self._find(self.STAKE_INPUT)
        return self

    def selection(self) -> SlipSelection:
        return SlipSelection(
            match=self._text(self.SELECTION_TEAMS),
            market=self._text(self.SELECTION_MARKET),
            odds=parse_money(self._text(self.SELECTION_ODDS)),
        )

    def enter_stake(self, stake: str) -> None:
        field = self._find(self.STAKE_INPUT)
        field.click()
        field.send_keys(Keys.END + Keys.BACKSPACE * len(field.get_attribute("value") or ""))
        field.send_keys(stake)
        self._wait_until(
            lambda _: field.get_attribute("value") == stake,
            f"stake input did not accept {stake!r}",
        )

    def total_stake(self) -> Decimal:
        return parse_money(self._text(self.TOTAL_STAKE))

    def potential_payout(self) -> Decimal:
        return parse_money(self._text(self.POTENTIAL_PAYOUT))

    def stake_warning(self) -> str | None:
        warnings = self.driver.find_elements(*self.STAKE_WARNING)
        return warnings[0].text.strip() if warnings else None

    def place_bet(self) -> None:
        self._click(self.PLACE_BET)

    def wait_until_placing(self) -> None:
        self._wait_until(
            lambda driver: self.PLACING_LABEL in driver.find_element(*self.PLACE_BET).text.lower(),
            "Place Bet button never showed the 'Placing...' state",
        )

    def is_place_bet_enabled(self) -> bool:
        return self._find(self.PLACE_BET).is_enabled()

    def is_empty(self) -> bool:
        return self._is_present(self.EMPTY_STATE) and not self._is_present(self.STAKE_INPUT)
