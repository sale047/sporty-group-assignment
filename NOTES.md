# Strategy & Recommendations

## Why these 2 tests were automated

I picked automation candidates by **risk x how often the check must be repeated x how stable it can be made**. Both tests guard money, both run against every build, and both are deterministic.

**1. E2E UI: place a single bet ([test_place_single_bet_e2e.py](automation/tests/ui/test_place_single_bet_e2e.py))**

- This is the critical revenue journey, and the only layer where UI and backend consistency can be verified. It checks that the slip, receipt and wallet show what the backend actually recorded. API tests cannot see a receipt with the wrong payout or reversed teams. Unit tests cannot see the header ignoring the new balance.
- Flow steps are hard assertions. Consistency checks after placement are soft assertions, so one run reports every mismatch. On the current build, a single run surfaces 5 defects: BUG-03, BUG-04, BUG-05, BUG-06 and BUG-08.
- It beat these other candidates:
  - The error modal / Rebet path needs fault injection, which makes it more brittle, and that path is used less often.
  - Filters have lower business impact.
  - Double-click placement is a destructive bug reproduction, not a regression check. It is covered by an assertion inside this test instead: the button must be disabled while "Placing...".

**2. API: stake rules ([test_place_bet_stake_rules.py](automation/tests/api/test_place_bet_stake_rules.py))**

- Stake limits and the balance check are the financial guard rails. The backend is the real enforcement point, because the UI can be bypassed. Both Critical bugs (BUG-01, BUG-02) live here, and neither is visible from the UI's own validation.
- It is fast (milliseconds per case), needs no browser, and is stable. One data-driven test covers 9 boundary and negative cases and checks the persisted balance after each one. New rules (selection, matchId, protocol errors) are one `pytest.param` away.
- It beat these other candidates:
  - UI stake validation is slower and duplicates the API with less authority.
  - Concurrency / 409 tests are timing-dependent, so they would be flaky.
  - `reset-balance` is test infrastructure rather than a user-facing feature.

**How known bugs are handled.** In the API test, each known defect is an `xfail(strict=True, raises=AssertionError)` on its own case. The other 7 cases keep guarding, and a fix turns the case into XPASS, which fails the run and reminds us to remove the marker. The E2E test is a single journey, so marking it xfail would hide any new regression in it. It therefore stays **red** until the bugs are fixed.

## What stays manual and why

- **Exploratory testing and spec interpretation.** Most high-impact findings came from questioning behaviour, not from scripted checks: the double charge, the negative stake, past-posting, and stale balance. Automation guards what we already know; exploration finds what we don't.
- **Error modal, Rebet and Close (TC-04).** This needs fault injection. I triggered it by blocking requests through DevTools. It is worth automating once the backend offers a deterministic failure switch (see recommendations). Until then it is a manual check per release.
- **Filters and calendar widget (TC-06).** These are UI-heavy controls that change often and carry low business risk. The filtering logic is better covered by fast frontend unit tests than by Selenium.
- **Visual layout, copy, and UX details**, such as badge states, the empty state, and responsiveness. Human judgement is cheaper and more reliable than brittle visual assertions at this stage.
- **Timing and concurrency issues** (409 lock, multi-click). These are non-deterministic in a browser. After the fix, they should become deterministic API or component tests.

## Recommendations for scaling

1. **CI/CD with a fast gate and a full run.**
   - Use GitHub Actions. Run the API suite on every pull request as a quick gate, and run the UI E2E suite headless on merge and nightly.
   - Publish the pytest-html report and failure screenshots as build artifacts.
   - Add a browser matrix through Selenium Grid or containers when more browsers are in scope.
   - Treat every `xfail` as a linked, owned ticket, and review them in triage so they don't rot.

2. **Test data isolation and testability hooks.** The biggest current limiter is that all tests share one `user-id` and wallet. That forces sequential runs and creates 409 conflicts and order dependencies. I would ask for:
   - a way to provision a fresh user per run or per worker, which enables `pytest-xdist` parallelism;
   - a seed endpoint that sets an exact balance, which makes insufficient-balance and boundary tests one call and works around BUG-09;
   - a deterministic fault-injection switch (for example, a header that forces a 500), so the error modal and Rebet flow can be automated;
   - stable `data-testid` attributes. Today's `id`s work, but they are not a contract.

3. **Add cheaper test layers below the UI.**
   - **Contract tests** generated from the OpenAPI document (for example, schemathesis or jsonschema validation) would have caught BUG-10 (currency USD), BUG-13 (500 on malformed JSON) and BUG-14 (GET returns 200) automatically.
   - **Frontend unit and component tests** for slip maths, receipt mapping and filter predicates would catch BUG-04, BUG-05 and BUG-11 in milliseconds. These are one-line bugs: `stake * 2`, `away vs home`, and `>` instead of `>=`.
   - The E2E suite then stays small and focused on journeys.

**Spec clarifications to raise with the product owner:**
- Is the minimum stake €1.00 (section 3) or €1.01 (table 4.1)?
- Bet ID and placement timestamp should come from the server. Today the UI generates them, so they cannot be traced to a stored bet.
- Kickoff has a date but no time. When does a match stop being bettable, and should past matches be returned at all?
- In the odds filter, does a match qualify if *any* of its three prices is in range? The slider max is 10, while the business max odds is 1000.
- Which rounding rule applies to payout (half-up or half-even)?
- Which display format should the receipt use for the selection?
- Should numeric strings (`"10"`) be accepted as a stake?
