# Execution Results & Bug Reports

## Environment

| Item | Value |
| --- | --- |
| Application | <https://qae-assignment-tau.vercel.app/?user-id=candidate-lK0oEBSF2OFO> (footer: Version 1.0.0) |
| Browser | Google Chrome 154 (desktop, 1440x1000) |
| OS | macOS 26.5 |
| API client | curl / Python `requests` with header `x-user-id: candidate-lK0oEBSF2OFO` |
| Date | 2026-10-07 |

Evidence is stored in [evidence/](evidence/): screenshots (`*.png`) and a raw API request/response log ([api_evidence.txt](evidence/api_evidence.txt)).

## Execution summary (top 3 scenarios)

| ID | Title | Result | Defects |
| --- | --- | --- | --- |
| TC-01 | Place a single bet successfully | **Fail** | BUG-03, BUG-04, BUG-05, BUG-06, BUG-08 |
| TC-02 | Stake validation boundaries (UI + API) | **Fail** (UI pass, API fail) | BUG-02 |
| TC-03 | Stake exceeding balance is blocked | **Fail** | BUG-01 (BUG-06 makes it reachable from the UI) |

### TC-01 - Place a single bet successfully

The slip behaved correctly: Manchester Utd vs Chelsea, Match Winner: Home, odds 2.45, stake €10.00, potential payout €24.50 ([tc01_slip_before_place.png](evidence/tc01_slip_before_place.png)). The button switched to **Placing...** and odds buttons were disabled while in progress ([tc01_placing.png](evidence/tc01_placing.png)). However, the Place Bet button itself stayed enabled, and clicking it again placed additional bets (BUG-03). The backend deducted €10 (`GET /api/balance` went from 120 to 110).

The receipt and balance display failed ([tc01_receipt.png](evidence/tc01_receipt.png)):
- The receipt shows **Chelsea vs Manchester Utd** (BUG-05).
- The receipt shows a payout of **€20.00** instead of €24.50 (BUG-04).
- The receipt has no **Selection** field (BUG-08).
- The header and slip still show **€120.00**, even though the backend balance is €110.00 (BUG-06).

Closing the receipt correctly returned to an empty slip ([tc01_after_close.png](evidence/tc01_after_close.png)).

### TC-02 - Stake validation boundaries

**UI: pass.**

| Input | Field value | Message | Place Bet |
| --- | --- | --- | --- |
| `0.99` | 0.99 | "Minimum stake is €1.00" ([tc02_stake_0_99.png](evidence/tc02_stake_0_99.png)) | disabled |
| `0` | 0 | "Minimum stake is €1.00" | disabled |
| `1` / `1.00` | 1 / 1.00 | - | enabled |
| `100` / `100.00` | 100 / 100.00 | - | enabled |
| `100.01` | 100.01 | "Maximum stake is €100.00" ([tc02_stake_100_01.png](evidence/tc02_stake_100_01.png)) | disabled |
| `10.123` | 10.12 (truncated) | - | enabled |
| `abc` | empty | - | disabled |
| `-5` | 5 (minus stripped) | - | enabled |
| `1,5` | 1.5 | - | enabled |

**API: fail.**
- These cases behaved correctly: `0.99` and `0` returned 422 `invalid_stake_min`; `100.01` returned 422 `invalid_stake_max`; `10.123` and `1.005` returned 422 `invalid_stake_precision`; `"abc"`, `"10"` and `null` returned 422 `invalid_stake_type`; `1` and `100` returned 200 with the correct deduction.
- `-5` failed: it was **accepted with 200** and the balance **increased** by €5 (BUG-02).

### TC-03 - Stake exceeding balance is blocked

- **UI on a fresh page load: pass.** With balance €20, a stake of `20` was allowed. `20.01` and `50` showed "Insufficient balance" and disabled Place Bet ([tc03_insufficient.png](evidence/tc03_insufficient.png)).
- **UI without reload: fail.** With balance €20, the first €15 bet succeeded, but the header kept showing €20 (BUG-06). A second €15 bet was therefore allowed and also succeeded ([bug_overdraw_second_bet_success.png](evidence/bug_overdraw_second_bet_success.png)). After a reload, the balance was **€-10.00** ([bug_negative_balance_after_refresh.png](evidence/bug_negative_balance_after_refresh.png)).
- **API: fail.** With balance €25, a stake of 50 returned 200 and the balance became -25 (BUG-01).

## Exploratory notes

About 30 minutes, focused on the riskiest areas around placement: money handling, API contract, recovery path, and data the user relies on.

- **Error modal (TC-04, explored rather than formally executed): works as specified.** I made placement fail by blocking `/api/place-bet` through Chrome DevTools Protocol.
  - The title "Something went wrong" and the explanatory body are shown ([tc04_error_modal.png](evidence/tc04_error_modal.png)).
  - After unblocking, **Rebet** showed "Placing..." again and resulted in one success. The balance dropped from €120 to €115, so there was no double charge.
  - **Close** and **X** both cleared the selection and stake.
- **Concurrency:** 3 parallel `place-bet` requests returned one 200 and two 409 `bet_in_progress`, which is correct. Once, the user stayed locked with 409 for several seconds after the burst. I could not reproduce it reliably (2 parallel requests released the lock immediately), so it is recorded as an observation, not a bug.
- **API negative cases that behaved correctly:**
  - Missing or blank `x-user-id` returns 401 `missing_user_id`; an unknown user returns 401 `invalid_user_id`.
  - Unknown, blank or missing `matchId` returns 422 `invalid_match` / `invalid_match_id`.
  - `selection` of `home` (lowercase) or `WIN` returns 422 `invalid_selection`.
  - A JSON array body returns 400.
  - `PUT /api/place-bet`, `GET /api/reset-balance` and `POST /api/matches` return 405.
- **Odds filter:** two boundary defects (BUG-11, BUG-12) and a counter defect (BUG-15).
- **Stake input sanitizing is silent:** `1.2.3` becomes `1.23` and `1e2` becomes `12` without any feedback. This can make the user bet an amount they didn't type. It is low risk, because the stake and payout are visible before placing, but it is worth a UX decision.
- **Bet ID and timestamp are generated in the browser.** `POST /api/place-bet` returns no bet ID, and the UI creates a random `#B-xxxxx` and stamps the time when the button is clicked, before the request is even sent. The Bet ID cannot be used for support or reconciliation. This is listed as a spec clarification in [NOTES.md](../NOTES.md).

---

## Bug reports

Bugs are ordered by severity.

| ID | Title | Severity |
| --- | --- | --- |
| BUG-01 | API accepts a stake greater than the available balance (balance goes negative) | Critical |
| BUG-02 | API accepts a negative stake and increases the balance | Critical |
| BUG-03 | Place Bet stays clickable while "Placing...": repeated clicks place and charge multiple bets | Critical |
| BUG-04 | Success receipt shows a wrong potential payout (stake x 2 instead of stake x odds) | High |
| BUG-05 | Success receipt shows the teams in reversed order (away vs home) | High |
| BUG-06 | Header and bet slip balance are not updated after a successful bet | High |
| BUG-07 | Matches whose kickoff date is in the past are listed and accept bets | High |
| BUG-08 | Success receipt does not show the selection | Medium |
| BUG-09 | `POST /api/reset-balance` reports €125.50 but persists €120.00 | Medium |
| BUG-10 | `POST /api/place-bet` success response returns `currency: "USD"` | Medium |
| BUG-11 | Odds filter excludes matches whose odds equal the minimum bound | Medium |
| BUG-12 | Odds filter accepts an invalid range (min > max) without feedback | Medium |
| BUG-13 | Malformed JSON body returns 500 instead of 400 | Low |
| BUG-14 | `GET /api/place-bet` returns 200 instead of 405 | Low |
| BUG-15 | "Showing N matches" counter ignores active filters | Low |
| BUG-16 | Bet slip hides the available balance while a selection is active | Low |

### BUG-01 - API accepts a stake greater than the available balance (balance goes negative)

- **Severity:** Critical
- **Reproduction steps:**
  1. `POST /api/reset-balance`, then `POST /api/place-bet` with `{"matchId":"premier-league-manutd-chelsea","selection":"HOME","stake":100}`. The balance is now €25.
  2. `POST /api/place-bet` with `{"matchId":"premier-league-manutd-chelsea","selection":"AWAY","stake":50}`.
  3. `GET /api/balance`.
- **Expected:** Step 2 returns 422 with an insufficient-balance error (spec 4.1: "Must not exceed available balance - UI + API - reject as insufficient balance"), and the balance stays €25.
- **Actual:** Step 2 returns `200 Bet placed successfully` with `"balance":-25`, and `GET /api/balance` returns `-25`. The same is reachable **from the UI** without any tooling, because of BUG-06: with €20, two consecutive €15 bets both succeed and the balance becomes €-10.00.
- **Business impact:** Users can wager money they don't have. That is direct credit and financial loss for the operator and a regulatory breach in real-money gambling.
- **Evidence:** [api_evidence.txt](evidence/api_evidence.txt) (section "insufficient balance not enforced"), [bug_overdraw_second_bet_success.png](evidence/bug_overdraw_second_bet_success.png), [bug_negative_balance_after_refresh.png](evidence/bug_negative_balance_after_refresh.png).

### BUG-02 - API accepts a negative stake and increases the balance

- **Severity:** Critical
- **Reproduction steps:**
  1. `GET /api/balance` returns 120.
  2. `POST /api/place-bet` with `{"matchId":"premier-league-manutd-chelsea","selection":"HOME","stake":-5}`.
  3. `GET /api/balance`.
- **Expected:** 422 `invalid_stake_min` (spec 4.1: stake must be positive and at least €1.00). The balance is unchanged.
- **Actual:** `200 Bet placed successfully`, `"stake":-5`, `"payout":-12.25`, and the balance is **125**. Each request adds money. Other below-minimum values (`0`, `0.99`) are rejected correctly, so the minimum check only fails for negative numbers.
- **Business impact:** Anyone with API access can mint unlimited balance with a simple script. This is direct financial loss and a fraud vector. The UI strips the minus sign, but the UI is not a security boundary.
- **Evidence:** [api_evidence.txt](evidence/api_evidence.txt) (section "negative stake accepted").

### BUG-03 - Place Bet stays clickable while "Placing...": repeated clicks place and charge multiple bets

- **Severity:** Critical
- **Reproduction steps:**
  1. Reset the balance. `GET /api/balance` returns 120.
  2. Open the app, click odds **1** on Real Madrid vs Barcelona and enter stake `10`.
  3. Click **Place Bet**. While the button shows "Placing...", click it twice more (about 200 ms apart).
  4. Wait for the receipt, then call `GET /api/balance`.
- **Expected:** Once submission starts, the button is disabled and further clicks are ignored (spec 2.3: in-progress state resolving to **one** final outcome). Exactly one bet is placed and €10 is deducted.
- **Actual:** The button stays enabled and clickable while showing "Placing...". Each click starts a new submission. Only one receipt is shown, but the balance drops from **€120 to €90**: three bets were placed and charged. The API's 409 "bet in progress" guard does not help, because the UI adds a random 1-4 s delay before each request, so the requests rarely overlap.
- **Business impact:** Impatient users who double-click are charged several times for one intended bet and only see one receipt. This leads to direct customer financial harm, chargebacks, and complaints.
- **Evidence:** [bug_double_click_placing.png](evidence/bug_double_click_placing.png) (button enabled during "Placing..."). Balance before/after was captured via the API (120 to 90).

### BUG-04 - Success receipt shows a wrong potential payout (stake x 2 instead of stake x odds)

- **Severity:** High
- **Reproduction steps:**
  1. Open the app and click odds **1** (2.45) on Manchester Utd vs Chelsea.
  2. Enter stake `10`. The slip shows Potential Payout €24.50.
  3. Click **Place Bet** and wait for the receipt.
- **Expected:** Potential payout on the receipt is €24.50 (stake x odds at placement), consistent with the slip and with the API response (`"payout":24.5`).
- **Actual:** The receipt shows **€20.00**. With other odds the receipt is always stake x 2. For example, €5 at odds 4.10 shows €10.00 instead of €20.50.
- **Business impact:** The receipt is the customer's record of the bet. A wrong payout leads to disputes and complaints when the bet settles, and undermines trust in the product.
- **Evidence:** [tc01_slip_before_place.png](evidence/tc01_slip_before_place.png) vs [tc01_receipt.png](evidence/tc01_receipt.png).

### BUG-05 - Success receipt shows the teams in reversed order (away vs home)

- **Severity:** High
- **Reproduction steps:** Same as BUG-04, on match Manchester Utd (home) vs Chelsea (away).
- **Expected:** The receipt shows `Manchester Utd vs Chelsea`, with the home team first, as in the match list and slip (domain rule: "This convention carries through to the bet receipt").
- **Actual:** The receipt shows `Chelsea vs Manchester Utd`.
- **Business impact:** With 1/X/2 markets, the team order defines what "Home" means. The customer can believe they backed the other team, which leads to disputes and support load.
- **Evidence:** [tc01_receipt.png](evidence/tc01_receipt.png).

### BUG-06 - Header and bet slip balance are not updated after a successful bet

- **Severity:** High
- **Reproduction steps:**
  1. Open the app. The header shows €120.00.
  2. Place a €10 bet successfully and close the receipt.
  3. Compare the header and slip balance with `GET /api/balance`.
- **Expected:** The stake is deducted in the UI immediately (spec 2.3: "On success: stake is deducted"). The header and slip show €110.00.
- **Actual:** The header and slip keep showing €120.00 until a page reload. The API response already contains the new balance (`"balance":110`), but the UI ignores it.
- **Business impact:** Users see more money than they have. Because client-side "Insufficient balance" validation uses this stale value, it combines with BUG-01 to let users overdraw from the normal UI.
- **Evidence:** [tc01_receipt.png](evidence/tc01_receipt.png) (header €120.00 after the bet), [bug_overdraw_second_bet_success.png](evidence/bug_overdraw_second_bet_success.png).

### BUG-07 - Matches whose kickoff date is in the past are listed and accept bets

- **Severity:** High
- **Reproduction steps:**
  1. Open the app on 2026-10-07. The first matches have kickoff dates such as Fri 27 Feb and carry a **PAST** badge. Their odds buttons are enabled.
  2. Place a bet on Manchester Utd vs Chelsea (`kickoffDate` 2026-02-27) through the UI, or via `POST /api/place-bet`.
- **Expected:** Only upcoming matches are listed and bettable (spec 1 and 3: "Upcoming matches only"). The API rejects bets on matches that have already started.
- **Actual:** 82 of the 103 matches returned by `GET /api/matches` are in the past. The page title still says "Upcoming Football Matches", and bets on them are accepted (200).
- **Business impact:** Accepting bets on events whose result is already known ("past-posting") is a guaranteed loss scenario for a sportsbook and is exploitable.
- **Note:** This may be partly caused by static test data getting old. The defect still stands, because the API does not validate kickoff time and the UI does not block PAST matches.
- **Evidence:** [bug_past_matches_listed.png](evidence/bug_past_matches_listed.png), [api_evidence.txt](evidence/api_evidence.txt) (section "past match accepted").

### BUG-08 - Success receipt does not show the selection

- **Severity:** Medium
- **Reproduction steps:** Same as BUG-04.
- **Expected:** The receipt shows the selection (spec 2.4: Bet ID, Match details, **Selection**, Stake, Odds, Potential payout, Timestamp), for example "Match Winner: Home".
- **Actual:** The receipt shows Bet ID, match, stake, odds, payout and time, but no selection.
- **Business impact:** The customer cannot confirm what they bet on. Combined with BUG-05, the receipt does not identify the bet at all.
- **Evidence:** [tc01_receipt.png](evidence/tc01_receipt.png).

### BUG-09 - `POST /api/reset-balance` reports €125.50 but persists €120.00

- **Severity:** Medium
- **Reproduction steps:**
  1. `POST /api/reset-balance` returns `{"balance":125.5,"currency":"EUR"}`.
  2. `GET /api/balance` immediately after.
- **Expected:** The balance is €125.50, matching the response and the documented initial balance (spec 5.3: "Response body and persisted state must be consistent after reset").
- **Actual:** `GET /api/balance` returns `120`. This was reproduced 4 times in a row, and the UI also shows €120.00 after a reset.
- **Business impact:** Any tooling, support action or automated test that trusts the reset response works with a wrong balance. This erodes confidence in the environment and test data.
- **Evidence:** [api_evidence.txt](evidence/api_evidence.txt) (first two sections).

### BUG-10 - `POST /api/place-bet` success response returns `currency: "USD"`

- **Severity:** Medium
- **Reproduction steps:** `POST /api/place-bet` with any valid body.
- **Expected:** `"currency":"EUR"` (spec 3: Currency EUR; `GET /api/balance` and `reset-balance` both return EUR).
- **Actual:** `"currency":"USD"` on every successful placement.
- **Business impact:** Any consumer that trusts the response (app, wallet service, reporting) would label or convert amounts in the wrong currency.
- **Evidence:** [api_evidence.txt](evidence/api_evidence.txt) (every `200 Bet placed successfully` line).

### BUG-11 - Odds filter excludes matches whose odds equal the minimum bound

- **Severity:** Medium
- **Reproduction steps:**
  1. Open **Odds** filter, set Min `2.05`, Max `2.05`, and click Apply.
  2. Repeat with Min `1.35`, Max `1.45`.
- **Expected:** The bounds are inclusive (spec 2.6). Step 1 shows the 10 matches that have a 2.05 price. Step 2 shows the 3 matches with a price between 1.35 and 1.45, including PSG vs Marseille (1.35).
- **Actual:** Step 1 shows 0 matches and step 2 shows 2 (PSG vs Marseille missing). A match whose odds equal the minimum is excluded.
- **Business impact:** Users filtering for a price don't see matching markets, which loses bets.
- **Evidence:** [tc06_odds_equal_bounds.png](evidence/tc06_odds_equal_bounds.png).

### BUG-12 - Odds filter accepts an invalid range (min > max) without feedback

- **Severity:** Medium
- **Reproduction steps:** Open the **Odds** filter, set Min `3`, Max `2`, and click Apply.
- **Expected:** The range is rejected with clear feedback (spec 2.6), for example "Min must be lower than or equal to Max", and it is not applied.
- **Actual:** The filter is applied ("Odds: 3.00 - 2.00") and the match list goes blank, with no message or empty state.
- **Business impact:** The user sees an empty sportsbook and may think there are no matches.
- **Evidence:** [tc06_odds_invalid_range.png](evidence/tc06_odds_invalid_range.png).

### BUG-13 - Malformed JSON body returns 500 instead of 400

- **Severity:** Low
- **Reproduction steps:** `POST /api/place-bet` with header `Content-Type: application/json` and body `{bad`.
- **Expected:** 400 `invalid_json` "Malformed JSON body." (spec 4.3 and the Swagger example).
- **Actual:** 500 `internal_server_error`.
- **Business impact:** Client errors are reported as server failures. This pollutes error-rate monitoring and alerting, and shows an unhandled parsing path.
- **Evidence:** [api_evidence.txt](evidence/api_evidence.txt).

### BUG-14 - `GET /api/place-bet` returns 200 instead of 405

- **Severity:** Low
- **Reproduction steps:** `GET /api/place-bet` with a valid `x-user-id`.
- **Expected:** 405 `method_not_allowed` (spec 4.3), as `PUT` on the same endpoint already does.
- **Actual:** `200 {}`.
- **Business impact:** It breaks the API contract and can hide client bugs, because a wrong method looks like success.
- **Evidence:** [api_evidence.txt](evidence/api_evidence.txt).

### BUG-15 - "Showing N matches" counter ignores active filters

- **Severity:** Low
- **Reproduction steps:** Apply any odds filter, for example Min `3`, Max `2`, or Min `1.35`, Max `1.45`.
- **Expected:** The counter shows the number of visible matches.
- **Actual:** It always shows "Showing 103 matches".
- **Business impact:** Misleading information, minor UX issue.
- **Evidence:** [tc06_odds_invalid_range.png](evidence/tc06_odds_invalid_range.png) (0 matches visible, counter says 103).

### BUG-16 - Bet slip hides the available balance while a selection is active

- **Severity:** Low
- **Reproduction steps:** Click any odds button.
- **Expected:** The bet slip shows the entered stake, **available balance** and potential payout (spec 2.2).
- **Actual:** "Balance: €X" is visible only while the slip is empty. Once a selection is added, it disappears from the slip.
- **Business impact:** The user has to look elsewhere to decide on a stake. Minor UX issue.
- **Evidence:** [tc01_slip_before_place.png](evidence/tc01_slip_before_place.png) vs [tc01_after_close.png](evidence/tc01_after_close.png).
