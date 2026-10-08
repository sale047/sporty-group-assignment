from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

WINDOW_SIZE = "1440,1000"


def create_chrome_driver(headless: bool) -> WebDriver:
    options = webdriver.ChromeOptions()
    options.add_argument(f"--window-size={WINDOW_SIZE}")
    options.add_argument("--disable-search-engine-choice-screen")
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(0)
    return driver
