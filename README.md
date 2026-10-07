# Sporty Group - QA Engineer Home Assignment

QA submission for the **Single Bet Placement** feature of <https://qae-assignment-tau.vercel.app/>, using user ID `candidate-lK0oEBSF2OFO`.

## Deliverables

| Part | Deliverable | Location |
| --- | --- | --- |
| A1 | Test plan (6 prioritized scenarios) | [manual/TEST_PLAN.md](manual/TEST_PLAN.md) |
| A2 | Execution results (top 3) and bug reports | [manual/EXECUTION_RESULTS.md](manual/EXECUTION_RESULTS.md), evidence in [manual/evidence/](manual/evidence/) |
| B | Automation framework + 2 tests | [automation/](automation/) |
| C | Strategy & recommendations | [NOTES.md](NOTES.md) |

## Repository layout

```
manual/                         Part A: test plan, execution results, bug reports, evidence
NOTES.md                        Part C: strategy and recommendations
automation/                     Part B
  config/settings.py            environment-driven configuration
  framework/
    api/client.py               BettingApiClient (requests.Session with x-user-id)
    api/models.py               Match, Selection
    ui/driver_factory.py        Chrome setup (headed or headless)
    ui/pages/base_page.py       explicit-wait helpers shared by all page objects
    ui/pages/betting_page.py    header, match list, result modals
    ui/components/bet_slip.py   bet slip component
    ui/components/receipt_modal.py
    utils/money.py              Decimal money parsing and maths
    utils/soft_assert.py        collects E2E consistency checks
  tests/api/test_place_bet_stake_rules.py
  tests/ui/test_place_single_bet_e2e.py
  conftest.py                   fixtures and screenshot-on-failure hook
  pytest.ini                    markers, HTML report, strict xfail
```

## Automation setup

**Prerequisites:** Python **3.10+** (developed on 3.12) and the latest desktop Google Chrome. You don't need to install a chromedriver: Selenium Manager downloads a matching one on first run.

```bash
cd automation
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the tests

Run every command from the `automation/` directory.

```bash
pytest                 # both tests (UI opens a visible Chrome window)
HEADLESS=1 pytest      # headless Chrome
pytest -m api          # API test only
pytest -m ui           # E2E UI test only
```

The HTML report is written to `automation/reports/report.html`. When a UI test fails, a screenshot is embedded in the report and saved to `automation/reports/screenshots/`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BASE_URL` | `https://qae-assignment-tau.vercel.app` | Application under test |
| `USER_ID` | `candidate-lK0oEBSF2OFO` | Sent as `?user-id=` and the `x-user-id` header |
| `HEADLESS` | `0` | `1` runs Chrome headless |
| `UI_TIMEOUT` | `15` | Explicit wait timeout, in seconds |
| `API_TIMEOUT` | `10` | HTTP timeout, in seconds |

### Expected result on the current build

The run ends with **7 passed, 2 xfailed, 1 failed**. Each non-passing result is caused by a reported product defect, not by a problem in the framework.

| Test | Result | Reason |
| --- | --- | --- |
| `test_place_bet_enforces_stake_rules` (9 cases) | 7 passed, 2 xfailed | `negative` is BUG-02. `exceeds-balance` is BUG-01. |
| `test_place_single_bet_end_to_end` | failed, reporting 5 checks | BUG-03 (Place Bet not locked while placing), BUG-05 (teams reversed), BUG-08 (selection missing), BUG-04 (payout = stake x 2), BUG-06 (header balance not updated) |

Known API defects are marked `xfail(strict=True)`, so when a bug is fixed the case shows up as XPASS and fails the run as a reminder to remove the marker. The E2E journey stays red on purpose; the reasoning is in [NOTES.md](NOTES.md).

## Design decisions

- **Page Object Model with components.** `BettingPage` owns page-level elements. The bet slip and receipt are separate components, so tests read like the user journey and locators live in one place. Locators use the app's stable `id`s, such as `odds-<matchId>-home` and `bet-slip-stake-input`.
- **Explicit waits only.** The implicit wait is 0. Placement has a random 1-4 s client delay, so all synchronisation goes through `WebDriverWait` conditions, never through `sleep`.
- **The API client returns raw responses.** Status codes and error bodies are often the thing under test, so assertions stay in the tests. The `fetch_*` helpers are for setup and verification and fail fast.
- **Money is compared as `Decimal`**, parsed from UI text or API numbers, to avoid float noise such as `10 * 2.45`.
- **Test data comes from the live API.** Tests use the first *upcoming* match from `GET /api/matches` instead of hard-coded IDs. Each test resets the wallet and then reads the **persisted** balance, because the reset response is wrong (BUG-09).
- **Tests run sequentially.** All tests share one `user-id` and wallet, and the API returns 409 for concurrent bets from the same user. For that reason `pytest-xdist` is intentionally not used (see NOTES for how to unlock parallelism).

## Tooling choices

| Tool | Why |
| --- | --- |
| Python 3.12 + `venv` + `requirements.txt` | Required stack. Plain pip keeps setup to three commands, with no extra tool for reviewers to install. Versions are pinned for reproducibility. |
| Selenium 4 + pytest | Required stack. Selenium Manager removes manual driver management. |
| requests | Required for API testing. A shared `Session` carries the auth header. |
| pytest-html | A single self-contained HTML report with embedded failure screenshots. It is the only extra dependency. |
