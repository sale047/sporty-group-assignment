import base64
import re
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from framework.api.client import BettingApiClient
from framework.api.models import Match
from framework.ui.driver_factory import create_chrome_driver

SCREENSHOT_DIR = Path(__file__).parent / "reports" / "screenshots"


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture(scope="session")
def api(settings: Settings) -> Iterator[BettingApiClient]:
    client = BettingApiClient(settings.base_url, settings.user_id, settings.api_timeout)
    yield client
    client.close()


@pytest.fixture(scope="session")
def upcoming_match(api: BettingApiClient) -> Match:
    upcoming = [match for match in api.fetch_matches() if match.is_upcoming()]
    if not upcoming:
        pytest.skip("The match catalog has no upcoming matches")
    return upcoming[0]


@pytest.fixture
def starting_balance(api: BettingApiClient) -> Decimal:
    # The reset response can't be trusted (BUG-09), so read the stored balance instead.
    api.reset_balance().raise_for_status()
    return api.fetch_balance()


@pytest.fixture
def driver(settings: Settings) -> Iterator[WebDriver]:
    web_driver = create_chrome_driver(headless=settings.headless)
    yield web_driver
    web_driver.quit()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    report = yield
    web_driver = getattr(item, "funcargs", {}).get("driver")
    if report.when == "call" and report.failed and web_driver is not None:
        _attach_screenshot(item, report, web_driver)
    return report


def _attach_screenshot(item: pytest.Item, report: pytest.TestReport, web_driver: WebDriver) -> None:
    png = web_driver.get_screenshot_as_png()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    (SCREENSHOT_DIR / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', item.name)}.png").write_bytes(png)

    html_plugin = item.config.pluginmanager.getplugin("html")
    if html_plugin is not None:
        report.extras = [*getattr(report, "extras", []), html_plugin.extras.png(base64.b64encode(png).decode())]
