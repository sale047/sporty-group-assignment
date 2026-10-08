# Strategy & Recommendations

## Why these 2 tests were automated

I picked by **risk x how often the check must be repeated x how stable it can be made**. Both tests guard money and should run on every build.

**1. E2E UI: place a single bet ([test_place_single_bet_e2e.py](automation/tests/ui/test_place_single_bet_e2e.py))**

- It is the main revenue journey, and the only layer where you can check that the slip, receipt and header show what the backend actually stored. Flow steps are hard assertions; the consistency checks after placement are soft, so one run reports every mismatch (BUG-03, BUG-04, BUG-05, BUG-06, BUG-08 on the current build).
- Other candidates: the error modal / Rebet path needs fault injection and is used less often, and filters have lower business impact. Double-click is covered inside this test by asserting the button is disabled while "Placing...".

**2. API: stake rules ([test_place_bet_stake_rules.py](automation/tests/api/test_place_bet_stake_rules.py))**

- The backend is the real enforcement point, because the UI can be bypassed. Both Critical API bugs (BUG-01, BUG-02) are here and can't be seen from the UI's own validation. The test is fast and stable: one data-driven test covers 9 boundary and negative cases and checks the persisted balance after each.
- Other candidates: UI stake validation is slower and duplicates the API with less authority, and 409 concurrency tests would be timing-dependent.

**Known bugs.** Each known API defect is an `xfail(strict=True)` case, so the other cases keep guarding and a fix shows up as XPASS until the marker is removed. The E2E test stays **red**, because marking a whole journey xfail would hide new regressions in it.

## What stays manual and why

- **Exploratory testing.** The highest-impact findings (double charge, negative stake, past-posting, stale balance) came from questioning behaviour, not from scripted checks.
- **Error modal, Rebet and Close (TC-04).** Needs fault injection. Worth automating once the backend has a deterministic failure switch.
- **Filters (TC-06), layout and copy.** Low business risk and they change often. Filter logic is better covered by frontend unit tests than by Selenium.
- **Timing and concurrency (409 lock, multi-click).** Non-deterministic in a browser. After the fix they should become API or component tests.

## Recommendations for scaling

1. **CI with a fast gate.** Run the API suite on every pull request and the UI suite headless on merge and nightly (for example GitHub Actions). Publish the HTML report and screenshots as artifacts, and link every `xfail` to an owned ticket.
2. **Test data isolation and testability hooks.** All tests share one `user-id` and wallet, which forces sequential runs and causes 409s. I'd ask for a fresh user per run (enables `pytest-xdist`), an endpoint that sets an exact balance (also works around BUG-09), a switch that forces a 500 for the error flow, and stable `data-testid` attributes.
3. **Cheaper test layers below the UI.** Contract tests from the OpenAPI document would catch BUG-10, BUG-13 and BUG-14. Frontend unit tests for slip maths, receipt mapping and filters would catch BUG-04, BUG-05 and BUG-11, which are one-line bugs. The E2E suite then stays small.

**Spec questions for the product owner:**
- Is the minimum stake €1.00 (section 3) or €1.01 (table 4.1)?
- Kickoff has a date but no time. When does a match stop being bettable?
- Should the Bet ID and timestamp come from the server? Today the UI generates them.
- Which rounding rule applies to payout?
- In the odds filter, does a match qualify if *any* of its three prices is in range?
