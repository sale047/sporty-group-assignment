from dataclasses import dataclass
from decimal import Decimal

from selenium.webdriver.common.by import By

from framework.ui.pages.base_page import BasePage
from framework.utils.money import parse_money


@dataclass(frozen=True)
class Receipt:
    bet_id: str
    match: str
    stake: Decimal
    odds: Decimal
    payout: Decimal
    placed_at: str
    full_text: str


class ReceiptModal(BasePage):
    ROOT = (By.ID, "modal-success")
    BET_ID = (By.ID, "modal-success-bet-id")
    MATCH = (By.ID, "modal-success-match")
    STAKE = (By.ID, "modal-success-stake")
    ODDS = (By.ID, "modal-success-odds")
    PAYOUT = (By.ID, "modal-success-payout")
    PLACED_AT = (By.ID, "modal-success-placed-at")
    CLOSE = (By.ID, "modal-success-close")

    def wait_until_visible(self) -> "ReceiptModal":
        self._find(self.ROOT)
        return self

    def read(self) -> Receipt:
        return Receipt(
            bet_id=self._text(self.BET_ID),
            match=self._text(self.MATCH),
            stake=parse_money(self._text(self.STAKE)),
            odds=parse_money(self._text(self.ODDS)),
            payout=parse_money(self._text(self.PAYOUT)),
            placed_at=self._text(self.PLACED_AT),
            full_text=self._text(self.ROOT),
        )

    def close(self) -> None:
        self._click(self.CLOSE)
        self._wait_until_gone(self.ROOT)
