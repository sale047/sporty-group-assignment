from typing import Callable, TypeVar

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

Locator = tuple[str, str]
T = TypeVar("T")


class BasePage:
    def __init__(self, driver: WebDriver, timeout: float) -> None:
        self.driver = driver
        self.timeout = timeout
        self._wait = WebDriverWait(driver, timeout)

    def _find(self, locator: Locator) -> WebElement:
        return self._wait.until(EC.visibility_of_element_located(locator), f"{locator} not visible")

    def _click(self, locator: Locator) -> None:
        self._wait.until(EC.element_to_be_clickable(locator), f"{locator} not clickable").click()

    def _text(self, locator: Locator) -> str:
        return self._find(locator).text.strip()

    def _is_present(self, locator: Locator) -> bool:
        return bool(self.driver.find_elements(*locator))

    def _wait_until(self, condition: Callable[[WebDriver], T], message: str) -> T:
        return self._wait.until(condition, message)

    def _wait_until_gone(self, locator: Locator) -> None:
        self._wait.until(EC.invisibility_of_element_located(locator), f"{locator} still visible")
