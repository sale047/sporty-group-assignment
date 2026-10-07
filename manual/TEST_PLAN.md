# Test Plan - Single Bet Placement

## Scope

**In scope:** single pre-match football bet placement on desktop Chrome: match list, odds selection, bet slip, stake validation (UI and API), place-bet lifecycle (loading, success receipt, error modal), balance handling and the date/odds filters.

**Out of scope (per spec):** live betting, multi-bets, other sports, mobile UX.

**Application:** <https://qae-assignment-tau.vercel.app/?user-id=candidate-lK0oEBSF2OFO>
**API docs:** `/api/docs` (Swagger), all endpoints require the `x-user-id` header.

## Prioritization approach

The scenarios are ranked by **business impact x likelihood of failure**:

1. **Money integrity comes first.** Anything that can move the wrong amount of money, let a user bet money they don't have, or show a customer wrong bet details is Critical. These failures cause direct financial loss, disputes, and regulatory exposure.
2. **The core journey comes next.** If placing a bet fails, the product earns nothing.
3. **Recovery paths and convenience features come last.** These are the error modal, slip management, and filters. They hurt UX and conversion, but they don't directly move money.

I check validation rules at **both layers (UI and API)**. The spec explicitly requires both, and a UI-only check can be bypassed by anyone calling the API directly.

| ID | Title | Priority |
| --- | --- | --- |
| TC-01 | Place a single bet successfully: receipt and balance are consistent | Critical |
| TC-02 | Stake validation boundaries (min / max / precision / type) on UI and API | Critical |
| TC-03 | Stake exceeding available balance is blocked on UI and API | Critical |
| TC-04 | Failed placement: error modal, Rebet and Close behave as specified | High |
| TC-05 | Single active selection: replace, remove (x) and Remove All | Medium |
| TC-06 | Odds and date filters: inclusive bounds and invalid range feedback | Medium |

Top 3 (executed): **TC-01, TC-02, TC-03.**

---

## Scenarios

### TC-01 - Place a single bet successfully: receipt and balance are consistent

- **Priority:** Critical
- **Risk rationale:** This is the revenue-generating journey and the one every user takes. Every value shown to the user (match, selection, stake, odds, payout, balance) must match what the backend recorded. Any mismatch either costs money or creates a customer dispute ("the receipt said I'd win €24.50").
- **Preconditions:** Valid `user-id` in the URL. Balance is known (`GET /api/balance`) and is at least €10. Pick an upcoming match.
- **Steps:**
  1. Open the app with `?user-id=<id>`. Note the header balance.
  2. Click odds **1** (home) on an upcoming match. Note the teams and odds.
  3. Verify that the bet slip shows the selection (`Home vs Away`, `Match Winner: Home`, odds) and the available balance.
  4. Enter stake `10`.
  5. Verify that Total Stake = €10.00 and Potential Payout = `10 x odds`.
  6. Click **Place Bet**.
  7. Verify that the button shows **Placing...** and is not clickable while in progress.
  8. Wait for the outcome.
  9. Verify the success receipt fields.
  10. Close the receipt.
- **Expected result:**
  - Exactly one final outcome: the success receipt.
  - The receipt shows a Bet ID, match `Home vs Away` (home team first), selection, stake €10.00, odds at placement, potential payout = `stake x odds`, and placement timestamp. All values equal what the slip showed before placement.
  - The balance drops by exactly €10.00 in the header, in the bet slip and in `GET /api/balance`.
  - After closing, the slip is empty and no odds button is selected.

### TC-02 - Stake validation boundaries (min / max / precision / type) on UI and API

- **Priority:** Critical
- **Risk rationale:** Stake limits are business and responsible-gambling rules. Boundaries are where off-by-one and float bugs live. The API is the real enforcement point; the UI only mirrors it. Note that the spec is ambiguous: section 3 says min €1.00, while table 4.1 says €1.01. I test against €1.00, because it matches the UI copy and the API message, and I raise it as a clarification.
- **Preconditions:** Balance is at least €100. A selection is added to the slip.
- **Steps (UI):** Enter each value in the stake input and observe the message and the Place Bet state: `0.99`, `1`, `1.00`, `100`, `100.00`, `100.01`, `0`, `10.123`, `abc`, `-5`, `1,5`.
- **Steps (API):** `POST /api/place-bet` with a valid `matchId`/`selection` and stake `0.99`, `0`, `-5`, `1.00`, `100.00`, `100.01`, `10.123`, `"abc"`, `"10"`. Check `GET /api/balance` after each call.
- **Expected result:**
  - UI: `0.99` and `0` show "Minimum stake is €1.00" and disable Place Bet. `100.01` shows "Maximum stake is €100.00" and disables Place Bet. `1`, `1.00`, `100`, `100.00` are accepted. The input never holds more than 2 decimals or non-numeric characters.
  - API: values below €1.00, including zero and negatives, return 422 `invalid_stake_min`. Above €100.00 returns 422 `invalid_stake_max`. More than 2 decimals returns 422 `invalid_stake_precision`. Non-numbers return 422 `invalid_stake_type`. €1.00 and €100.00 return 200.
  - Rejected requests never change the balance. Accepted requests deduct exactly the stake.

### TC-03 - Stake exceeding available balance is blocked on UI and API

- **Priority:** Critical
- **Risk rationale:** If users can bet money they don't have, the operator takes on credit risk, and in a real-money product this is also a compliance breach. It must hold even when the UI's view of the balance is stale (another tab, a previous bet), so the API check is the one that matters.
- **Preconditions:** Bring the balance below €100. For example, place a €100 bet so €20 remains.
- **Steps:**
  1. Reload the app and verify that the header shows the real balance.
  2. Add a selection and enter a stake equal to the balance (`20`).
  3. Enter balance + €0.01 (`20.01`), then `50`.
  4. Place a €15 bet, close the receipt, and **without reloading** try another €15 bet.
  5. Call the API directly: `POST /api/place-bet` with stake `50`.
- **Expected result:**
  - A stake equal to the balance is allowed.
  - Stakes above the balance show "Insufficient balance" and Place Bet is disabled.
  - After the first €15 bet, the UI balance is €5, so the second €15 bet is blocked.
  - The API rejects stakes above the balance with 422 and an insufficient-balance error.
  - The balance never goes below €0.

### TC-04 - Failed placement: error modal, Rebet and Close behave as specified

- **Priority:** High
- **Risk rationale:** Network or server failures will happen in production. A bad recovery path can double-charge the user (Rebet placing two bets), lose their selection, or leave the slip stuck in "Placing...". It is rated High rather than Critical because it is not the main path, but a double charge would escalate it.
- **Preconditions:** Make placement fail, for example by blocking `/api/place-bet` in DevTools (Network request blocking) or by going offline.
- **Steps:**
  1. Add a selection, enter stake `5`, block the request, and click Place Bet.
  2. Verify the error modal.
  3. Unblock the request and click **Rebet**.
  4. Repeat the failure, then click **Close**.
  5. Repeat the failure, then click the top-right **X**.
- **Expected result:**
  - The modal title is "Something went wrong" and the body says the bet could not be processed and suggests retrying.
  - Rebet closes the modal and retries: the button shows "Placing...", then the success receipt appears. The balance is deducted once.
  - Close and X close the modal and clear the selection and stake.
  - The balance is unchanged by failed attempts.

### TC-05 - Single active selection: replace, remove (x) and Remove All

- **Priority:** Medium
- **Risk rationale:** The slip must always reflect exactly one intended selection. A stale selection or stale odds after switching would place a bet the user did not intend. Rated Medium because the impact is limited to the slip state and it is easy to notice before placing.
- **Steps:**
  1. Select odds **1** on match A and enter stake `10`.
  2. Select odds **X** on match A, then odds **2** on match B.
  3. Click **x** on the selection.
  4. Add a selection again and click **Remove All**.
- **Expected result:**
  - Only one odds button is highlighted at any time.
  - The slip count stays at 1.
  - The slip shows the latest match, market and odds, and the payout is recalculated with the new odds.
  - Remove (x) and Remove All empty the slip, reset the stake and un-highlight the odds.

### TC-06 - Odds and date filters: inclusive bounds and invalid range feedback

- **Priority:** Medium
- **Risk rationale:** Filters affect discoverability (conversion), not money. The spec explicitly requires inclusive bounds and clear feedback for invalid odds ranges, which are classic boundary defects.
- **Steps:**
  1. Odds filter: apply min = max = an existing odds value (for example `2.05`).
  2. Odds filter: apply a narrow range (for example `1.35 - 1.45`) and compare with the API data.
  3. Odds filter: apply min > max (`3 - 2`).
  4. Date filter: pick a single day, then a range whose start and end days both contain matches.
  5. Check the "Showing N matches" counter for each case.
- **Expected result:**
  - Matches with an odds value equal to either bound are included.
  - An invalid range is rejected with a clear message and is not applied.
  - The date range includes matches on both the start and end day.
  - The counter reflects the filtered list.
