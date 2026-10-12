# Test history

Everything that has been checked on this app since the first build, in the order it happened, and where each check now lives in the automated suite (`validate_requirements.py`). The scripts under `tests/legacy/` are the original one-off scripts, kept for reference only: they point at the sandbox paths they were written in and are superseded by the suite.

## How testing was done

| Stage | Tool | What it was good for |
|---|---|---|
| Early builds | jsdom (Node) | Fast logic checks without a browser: no script errors, forms, recurrence, currency, payment plan maths |
| From the layout work on | Playwright + Chromium, phone (390x844, 360x760) and laptop (1280x860) | Real layout, sizes, colours, animations, clicks |
| Every change | Syntax check (`node --check` on the extracted script; later an ES2019 parse to catch syntax older Safari cannot read) | Catches a broken edit before anything is delivered |
| Every layout change | Screenshots reviewed by eye on phone and laptop | Spacing, wrapping, readability |

Network is always blocked in the sandbox, so live exchange rates show "offline" there. The suite now mocks the rate sources so those paths are tested too.

## Chronological log

Rounds 1 to 7 are reconstructed from my working notes: those early checks were run as one-off commands and only the scripts listed in later rounds were kept. Rounds 8 onward match the saved scripts exactly.

| # | When (feature round) | Check | Result | Now covered by |
|---|---|---|---|---|
| 1 | First build (habit tracker, CSV storage) | Page loads, no script errors; habit add / tick / edit / delete; quit habit settings | Passed | GEN-02, HAB-02..05 |
| 2 | Apple / Safari round | Viewport + apple meta tags present; storage fallback when browser storage unavailable; import and export of the data file | Passed | GEN-05, GEN-11, DAT-03..05 |
| 3 | Views round (list / week / month / year, animations, tags, statistics, Pomodoro, clock) | Each view renders; year view fits phone width; sort and tag filtering; Pomodoro counts down, pause / reset / modes, max 60 min; clock ticks | Passed after fixes (year view first needed shrinking to fit without side scroll) | HAB-01, 06..10, RSP-12, PD-01, PD-03, PD-05 |
| 4 | Planner and journal round | Page switcher; planner day / week / goals; recurring and one-off tasks; subtasks; journal entry save; Pomodoro keeps running across pages | Passed | GEN-09, PLN-01..06, JRN-01, PD-04 |
| 5 | Storage round (CSV removed, JSON auto-save + export, week view with hourly bubbles) | Data saved as one JSON document; export / import round-trip; hourly bubble position matches task time; selectable number of days | Passed | DAT-01..04, PLN-11, RSP-13 |
| 6 | Budget round (jsdom script `legacy/jsdom_smoke.js`) | Currency conversion with stored rate incl. AED; 4-weekly and monthly repeats; tags and tag autofill; payment-plan preview with extra payment; statistics breakdown controls (group by, period, include, show); weekly view day columns and scroller; page switching without errors | Passed (AED needed a built-in fallback rate; rates showed "offline" in the sandbox only because requests are blocked) | BUD-05..08, BUD-11..16, PD-07..11, PLN-09 |
| 7 | Layout fixes from screenshots | Pomodoro and exchange-rate rows no longer wrap on phones; budget summary tiles in one row; week bubbles readable in 7-column mode; "Payment plan" segment no longer wraps; clock shows AM/PM separately | Passed after fixes | RSP-10, RSP-11, PD-01, BUD-12 |
| 8 | Habit tabs / planner start day / budget layout round (`legacy/func_views_and_filters.py`) | Habit tabs List, Week, Month, Day, Year, Statistics with List default and no leftover view button; planner Week-start select defaults to Monday and persists; fixed week starts on Monday; rolling view starts today; budget summary above period tabs; 4 tiles in one row; Week / Month / Year each have a different chart; filter popover has Show / Include / Break down by; tag autofill; no console errors | All passed | HAB-01, PLN-08, PLN-09, BUD-01, BUD-02, BUD-15, GEN-02 |
| 9 | Shading and summary round (`legacy/func_shading_and_summary.py`, `legacy/func_period_summary_and_shading.py`) | Weekdays and weekends use two shades and the 5 + 2 pattern repeats (no alternating weeks); day strip and day view shade differently for weekday vs weekend; summary tiles are period-based, never animate, and update when an entry is added; payment plan lives in the + sheet (no separate button), opens its own sheet and saves | Passed after the alternating-week shading was removed and the summary reverted to period-based | PLN-10, BUD-02, BUD-04, BUD-12 |
| 10 | Width sweep (`legacy/overflow_360.py`) | No sideways scroll on every page and tab at 360 px | Passed | RSP-01..08 |
| 11 | Screenshot sweep (`legacy/screenshots_all_views.py`) | Every view at phone and laptop size looked at by eye | Passed after the fixes in round 7 | RSP-01..18 (measurable parts) |
| 12 | Journal hourly mood and emotion wheel (`legacy/journal_mood.py`) | Hour tiles render and the current hour is marked; wheel opens; core, specific and refinement choices save under the right hour; previous / next arrows auto-save; clear works; mood curve and legend appear; no overflow at phone width | Passed | JRN-03, 05..09 |
| 13 | Hour row as a single scrollable row (`legacy/journal_hour_row.py`) | One row only; current hour second from the right on phone (slot 4 of 5) and laptop (slot 8 of 9); arrows scroll | Passed | JRN-03, JRN-04 |
| 14 | Footer and GitHub packaging | Footer text and "v0.1" at bottom right on a phone screenshot; no horizontal overflow; zip contents checked | Passed | GEN-10 |
| 15 | "Page not loading offline" report | Searched for external dependencies: found the Google Fonts stylesheet (the only one); embedded the font; reloaded with the network off, no errors; checked only the exchange-rate lookups remain | Fixed | GEN-01, GEN-03, GEN-04 |
| 16 | "Buttons not working" report | Clicked + with network off and with browser storage blocked in Chromium: works. Code scanned and parsed as ES2019 to rule out syntax unsupported by older Safari: clean. Conclusion: the file was being opened in a preview that does not run scripts | No app bug found | GEN-03, GEN-11 |
| 17 | Selected days for budget entries and Rent category | New entry with Tue + Thu saves `days:[1,3]`; label "Tue, Thu" shown; Rent chip present; no errors | Passed | BUD-06, BUD-09, BUD-10 |
| 18 | Weight and calories in the journal (v0.2) | Weight saves in kg and shows change since last entry; kg / lb conversion and persistence; 30 / 90 day trend chart and empty state; calories add / remove / invalid input; goal edit and over-goal state; 14-day chart, legend and 7-day average; entries list, export and streak; no overflow at 320 px, panels side by side on a laptop, 16 px inputs. Phone and laptop screenshots reviewed | Passed (one test needed a tolerance for the entrance animation) | JRN-12..19 |

## Bugs the tests caught (and the fix)

| Bug | Found by | Fix |
|---|---|---|
| Replacement string with `\1` inserted literally into the icon map, breaking the script | Syntax check | Replaced with the explicit icon path |
| Pomodoro and exchange-rate rows wrapped on phones | Screenshot review | Smaller layout rules at 520 px and below |
| 7-column week bubbles unreadable | Screenshot review | Narrow mode with a minimum lane height |
| "Payment plan" tab text wrapped | Screenshot review | No-wrap, smaller font, wider segment |
| "· AM" appeared in the date line | Screenshot review | AM / PM moved into its own small element |
| Alternating-week shading instead of weekday / weekend shading | User feedback + shading test | Shading now by weekday / weekend only |
| Summary tiles refreshed on every view change | User feedback + stability test | Redraw only when the figures change |
| Page failed to load offline | User report | Font embedded in the file |
| Occasional empty storage after a reload in the automated tests (about 1 run in 10, `file://` pages in headless Chromium) | New suite, repeated runs | Not an app fault: the validator now serves the app over a local http server (like GitHub Pages) and a separate check (GEN-13) covers opening the file straight from disk |

## Notes on test reliability

- Several early "failures" were test mistakes rather than app bugs: selectors that assumed an index, tile positions measured mid-animation, looking for `svg` in HTML bar charts, and a missing `scrollLeft` value in jsdom. Each was confirmed with a targeted check.
- In the new suite, the first full run had 15 failures: 14 were test mistakes (clicking behind an open sheet, a hidden + button on the Journal page, expecting a popover heading in lower case, measuring a scrolled page) and 1 was a wrong expectation about the exchange-rate row (it is a rates line plus a status line by design). All were corrected in the tests; no app change was needed.
