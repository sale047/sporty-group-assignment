from decimal import Decimal
from urllib.parse import urlencode

from selenium.webdriver.common.by import By

from framework.api.models import Selection
from framework.ui.components.bet_slip import BetSlip
from framework.ui.components.receipt_modal import ReceiptModal
from framework.ui.pages.base_page import BasePage
from framework.utils.money import parse_money


class BettingPage(BasePage):
    """The single-page sportsbook: header, match list, bet slip and result modals."""

    HEADER_BALANCE = (By.ID, "header-balance")
    MATCH_LIST = (By.ID, "match-list")
    SUCCESS_MODAL = (By.ID, "modal-success")
    ERROR_MODAL = (By.ID, "modal-error")
    ERROR_MESSAGE = (By.ID, "modal-error-message")

    def open(self, base_url: str, user_id: str) -> "BettingPage":
        self.driver.get(f"{base_url}/?{urlencode({'user-id': user_id})}")
        # The list renders only after both /api/matches and /api/balance resolved.
        self._find(self.MATCH_LIST)
        return self

    @property
    def bet_slip(self) -> BetSlip:
        return BetSlip(self.driver, self.timeout)

    def header_balance(self) -> Decimal:
        return parse_money(self._text(self.HEADER_BALANCE))

    def select_odds(self, match_id: str, selection: Selection) -> BetSlip:
        self._click(self._odds_button(match_id, selection))
        return self.bet_slip.wait_until_has_selection()

    def wait_for_receipt(self) -> ReceiptModal:
        """Wait for the placement to resolve; fail fast with the error copy if it resolved to failure."""
        self._wait_until(
            lambda driver: driver.find_elements(*self.SUCCESS_MODAL) or driver.find_elements(*self.ERROR_MODAL),
            "bet placement never resolved to a success or error modal",
        )
        if self._is_present(self.ERROR_MODAL):
            raise AssertionError(f"Bet placement failed with error modal: {self._text(self.ERROR_MESSAGE)!r}")
        return ReceiptModal(self.driver, self.timeout).wait_until_visible()

    @staticmethod
    def _odds_button(match_id: str, selection: Selection) -> tuple[str, str]:
        return By.ID, f"odds-{match_id}-{selection.value.lower()}"
