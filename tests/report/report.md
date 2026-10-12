# Test report

Run 2026-10-12 10:41 · 115 passed · 0 failed · 0 skipped

## General, platform and look

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | GEN-01 | The app is one self-contained HTML file: apart from exchange-rate lookups it makes no network requests, and needs no CSS/JS/font files. |  |
| PASS | GEN-02 | No JavaScript or console errors occur on any page or tab (phone and laptop size). |  |
| PASS | GEN-03 | The app loads and its buttons work with the network completely offline. |  |
| PASS | GEN-04 | The Barlow Condensed font is embedded in the file (works offline, nothing fetched from Google). |  |
| PASS | GEN-05 | Apple/mobile support: viewport meta with safe-area, apple-mobile-web-app meta tags and theme colour are present. |  |
| PASS | GEN-06 | Dark theme: very dark page background and light text. |  |
| PASS | GEN-07 | No bold fonts: no visible element uses a font weight above 500, on any page. |  |
| PASS | GEN-08 | Buttons use drawn icons or text, never emoji (habit icon picker excluded). |  |
| PASS | GEN-09 | Page switcher lists Habits, Planner, Budget and Journal, and the chosen page is remembered after reload. |  |
| PASS | GEN-10 | Footer carries a very small, subtle disclaimer (no responsibility, no data collected, free to use) and "v0.2" at the bottom right. |  |
| PASS | GEN-11 | If browser storage is blocked the app still loads and works in memory without errors. |  |
| PASS | GEN-12 | Add button (+) is available on Habits, Planner and Budget and hidden on Journal; each opens the right sheet. |  |
| PASS | GEN-13 | Works the same when the file is opened directly from disk (file://) and when hosted over http(s) as on GitHub Pages. |  |

## Data storage, export and import

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | DAT-01 | Auto-save: every change is written to browser storage as one JSON document (habits, plan, journal, budget, plans, settings). |  |
| PASS | DAT-02 | Reloading restores habits, planner, journal, budget and payment plans from storage. |  |
| PASS | DAT-03 | Export file: Data menu downloads a .json file containing all data. |  |
| PASS | DAT-04 | Import file: choosing a valid export replaces the current data. |  |
| PASS | DAT-05 | Import rejects an invalid file with a message and leaves existing data untouched. |  |
| PASS | DAT-06 | Budget-only export produces a CSV (with header and one row per entry); the other data is not included. |  |
| PASS | DAT-07 | Settings persist across reloads: habit view, sort order, week start day, exchange-rate currencies, Pomodoro lengths, budget period. |  |

## UI resizing and responsiveness

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | RSP-01 | No sideways page scroll on any page or tab at 320 px wide. |  |
| PASS | RSP-02 | No sideways page scroll on any page or tab at 360 px wide. |  |
| PASS | RSP-03 | No sideways page scroll on any page or tab at 390 px wide. |  |
| PASS | RSP-04 | No sideways page scroll on any page or tab at 430 px wide. |  |
| PASS | RSP-05 | No sideways page scroll on any page or tab at 768 px wide. |  |
| PASS | RSP-06 | No sideways page scroll on any page or tab at 1024 px wide. |  |
| PASS | RSP-07 | No sideways page scroll on any page or tab at 1280 px wide. |  |
| PASS | RSP-08 | No sideways page scroll on any page or tab at 1920 px wide. |  |
| PASS | RSP-09 | Live resizing: shrinking from laptop to phone width and back re-flows the layout with no sideways scroll and no reload. |  |
| PASS | RSP-10 | Pomodoro timer stays on a single row from 320 px upward; the three exchange rates stay on one line from 360 px upward. |  |
| PASS | RSP-11 | Budget summary shows income, expense, savings and left in a single row at every width from 320 px. |  |
| PASS | RSP-12 | Habit year view fits without side scrolling on phones. |  |
| PASS | RSP-13 | Weekly planner shows 3 days by default on phones and 7 on laptops, and the user can change the count. |  |
| PASS | RSP-14 | Sheets/dialogs: bottom sheet on phones, centred dialog on laptops; always fully inside the viewport and scrollable. |  |
| PASS | RSP-15 | Touch-friendly: main tap targets (tabs, tick buttons, toolbar buttons, + button) are at least 28 px high; form fields use 16 px text so iOS does not zoom. |  |
| PASS | RSP-16 | The + button stays inside the viewport at every width and the page keeps room below the content so it never hides the footer text. |  |
| PASS | RSP-17 | Content is centred and capped to a readable maximum width on very wide screens. |  |
| PASS | RSP-18 | Habit cards use a multi-column grid on laptops and a single column on phones. |  |

## Habit tracker

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | HAB-01 | Habit views are tabs along the top in the order List (default), Week, Month, Day, Year, Statistics. |  |
| PASS | HAB-02 | Add a build habit with name, tags, icon and colour; it appears in the list and the header counts it. |  |
| PASS | HAB-03 | Ticking a habit today updates the header ("1 of 1 done"), the streak text and storage; ticking again undoes it. |  |
| PASS | HAB-04 | Quit habits: quit date, goal days and money saved per day; days since the quit date count as clean; tapping today logs a slip and restarts the streak. |  |
| PASS | HAB-05 | Tapping a habit name opens it for editing; Delete (after confirming) removes it. |  |
| PASS | HAB-06 | Tags: tag chips filter the list; typing in the tag field suggests existing tags. |  |
| PASS | HAB-07 | Sort button offers several orders and reorders the list (e.g. by name). |  |
| PASS | HAB-08 | Week, Month and Day views each show their own visualisation and the previous/next arrows change the period. |  |
| PASS | HAB-09 | Year view shows 12 month rows with one cell per day for every habit. |  |
| PASS | HAB-10 | Statistics tab shows overview tiles and per-habit benchmark metrics. |  |
| PASS | HAB-11 | Streak maths: a habit ticked on the last 5 consecutive days (incl. today) has a streak of 5; a gap resets it. |  |

## Planner and goals

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | PLN-01 | Planner tabs: Day, Rolling, Week, Goals, Statistics, in that order. |  |
| PASS | PLN-02 | Add a one-off task and complete it: it shows in the day list, the header reads "x of y tasks done today", and ticking updates it. |  |
| PASS | PLN-03 | Recurring tasks: repeat Once / Daily / chosen weekdays / Monthly; the weekday picker defaults to the current weekday and tasks only occur on the chosen days. |  |
| PASS | PLN-04 | Monthly repeat occurs on the same date each month. |  |
| PASS | PLN-05 | Subtasks can be added and ticked independently of the parent task. |  |
| PASS | PLN-06 | Goals: add a goal with start and target dates; link a task to it; the Goals tab lists it with a year timeline. |  |
| PASS | PLN-07 | Filter and sort: show all / hide recurring / recurring only, tag chips, and several sort orders. |  |
| PASS | PLN-08 | Week tab shows a fixed week from a chosen start day (default Monday) and the choice is remembered. |  |
| PASS | PLN-09 | Rolling view starts with today as the left-most day and loads further weeks when scrolling sideways. |  |
| PASS | PLN-10 | Weekdays and weekends have two different dark shades on every planner view (day strip, rolling, week) with a repeating 5+2 pattern. |  |
| PASS | PLN-11 | Timed tasks appear in the week/rolling grid at their hour as coloured bubbles. |  |
| PASS | PLN-12 | Planner statistics tab renders completion figures. |  |
| PASS | PLN-13 | Tags in the planner: tag chips filter the calendar, and the tag field offers suggestions from all pages. |  |

## Budget tracker

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | BUD-01 | Budget layout: summary tiles above the period tabs; tabs are Week, Month, Year (default Month). |  |
| PASS | BUD-02 | Each period has its own visualisation (week, month, year charts differ) and the summary figures follow the period. |  |
| PASS | BUD-03 | Summary maths: income, expense, savings and left are correct for a known set of entries. |  |
| PASS | BUD-04 | Summary tiles are not rebuilt or animated when a filter / same tab is chosen, never animate on period change, and do update when an entry is added. |  |
| PASS | BUD-05 | Entries: amount, category with colour, note, tags, date; the entry shows in the list and the header shows "Spent £x this month". |  |
| PASS | BUD-06 | Generic categories with distinct colours include Rent, Salary, Savings, Investments, Groceries, Bills, Transport etc., grouped into income / savings / expense. |  |
| PASS | BUD-07 | Default currency is GBP; other currencies (incl. AED) are converted using the live rate, and the rate used is stored with the entry. |  |
| PASS | BUD-08 | Repeat options: Once, Weekly, Selected days, Every 4 weeks, Monthly, Yearly (+ Until date). |  |
| PASS | BUD-09 | Selected days: choose any combination of weekdays (e.g. Tue + Thu); occurrences fall only on those days, starting from the entry date. |  |
| PASS | BUD-10 | Selected days with nothing chosen is refused; edits keep the chosen days. |  |
| PASS | BUD-11 | Recurrence rules: weekly = every 7 days, every 4 weeks = 28 days, monthly keeps the date (clamped to month end), yearly keeps the date; "until" stops it. |  |
| PASS | BUD-12 | Payment plan: full amount, APR, monthly payment and day; the schedule is generated until paid off; maths matches the standard amortisation formula. |  |
| PASS | BUD-13 | Extra (early) payments can be added to a plan and shorten it. |  |
| PASS | BUD-14 | Payment plans appear under "Recurring and payment plans" with progress and next payment. |  |
| PASS | BUD-15 | Filter popover: Show (all/spent/income/saved), Include (all/recurring/one-off), Break down by (category/tag); each changes the numbers shown. |  |
| PASS | BUD-16 | Breakdown shows every category / tag with its total amount and percentage of the whole. |  |
| PASS | BUD-17 | Tags on budget entries: chips filter the entries; the tag field suggests tags used anywhere in the app. |  |
| PASS | BUD-18 | Budget export button (CSV) is on the budget page. |  |

## Journal, hourly mood, emotion wheel, weight and calories

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | JRN-01 | Journal entry: day navigation, five mood buttons, grateful-for, notes; saved automatically; word count and entries list update. |  |
| PASS | JRN-02 | Journal search filters the entries list; tiles show entries, streak, words and average mood. |  |
| PASS | JRN-03 | Hourly mood is a single scrollable row of 24 hour slots; today's current hour is the second-from-last visible slot; future hours are disabled. |  |
| PASS | JRN-04 | Arrow buttons beside the hour row scroll it; they disable at the ends. |  |
| PASS | JRN-05 | Emotion wheel: 6 core emotions in the centre ring, 18 specific emotions in the outer ring, plus 2 refinements shown as chips once one is chosen. |  |
| PASS | JRN-06 | Saving an hour stores core/secondary/tertiary/note under that date and hour; the slot shows its colour and emotion name. |  |
| PASS | JRN-07 | Clear removes an hour; a day with nothing left is removed from storage. |  |
| PASS | JRN-08 | Previous/next hour arrows inside the wheel sheet auto-save the chosen emotion and move on; Next is disabled beyond the current hour today. |  |
| PASS | JRN-09 | Mood curve: a chart with one dot per logged hour, a legend of the emotions used and a one-line summary (check-ins, average feeling, most frequent). |  |
| PASS | JRN-10 | Wheel accessibility: segments are focusable buttons with labels, selectable with Enter/Space; text on every segment has readable contrast. |  |
| PASS | JRN-11 | Hourly moods are included in the export, show in the entries list ("n mood check-ins") and count as a journal entry. |  |
| PASS | JRN-12 | Weight: enter today's weight (decimals allowed); it is saved automatically in kg under the date, shows the change since the previous logged weight, and counts as a journal entry. |  |
| PASS | JRN-13 | Weight unit kg / lb: switching converts what is shown, storage stays in kg, and the choice is remembered (also in the exported settings). |  |
| PASS | JRN-14 | Weight trend chart: one dot per logged day with a line between them, axis labels and hover values; 30 / 90 day switch changes the window. |  |
| PASS | JRN-15 | Calories: choose a meal (Breakfast / Lunch / Dinner / Snack), enter kcal and an optional description, Add; the total, remaining amount and progress bar update; entries can be removed; invalid amounts are refused. |  |
| PASS | JRN-16 | Calorie goal: default 2,000, editable (500-20,000) and remembered; going over the goal says so and turns the bar and chart bar amber. |  |
| PASS | JRN-17 | Calories chart: last 14 days as bars against a dashed goal line, with legend (within / over goal), hover values and a 7-day average that matches the data. |  |
| PASS | JRN-18 | Weight and calories appear in the journal entries list, are exported / imported with the data, and count towards the journal streak. |  |
| PASS | JRN-19 | Weight and calories panels fit at 320 px (no sideways scroll), sit side by side on laptops, and their fields use 16 px text so iOS does not zoom. |  |

## Passive / automatic data (clock, timer, exchange rates, derived figures)

| Result | ID | Requirement | Detail |
|---|---|---|---|
| PASS | PD-01 | Clock: shows the current time and date, seconds tick, AM/PM is shown separately, and the date line has no stray separators. |  |
| PASS | PD-02 | Clock and Pomodoro sit in the same place on every page and are not rebuilt when switching pages. |  |
| PASS | PD-03 | Pomodoro: default 25:00 focus / 5:00 break; start counts down, pause holds, reset restores, switching mode sets the other length. |  |
| PASS | PD-04 | Pomodoro keeps running while switching between pages, and the browser tab title shows the countdown. |  |
| PASS | PD-05 | Pomodoro lengths are adjustable 1 to 60 minutes (never above 60) and are remembered. |  |
| PASS | PD-06 | Completing a focus session beeps (no error), counts "n sessions today" and switches to break. |  |
| PASS | PD-07 | Live exchange rates: three currencies are shown under the timer with an "updated" time when the source answers. |  |
| PASS | PD-08 | Exchange rates fall back to the next source if the first fails. |  |
| PASS | PD-09 | When every source fails the row says "offline · tap to retry", keeps the last known rates, and tapping retries. |  |
| PASS | PD-10 | Exchange-rate currencies are chosen from three drop-downs (AED included), shown immediately and remembered. |  |
| PASS | PD-11 | AED has a built-in peg (3.6725 per USD) when a source does not list it. |  |
| PASS | PD-12 | Header sub-title is live per page: habits done, tasks done, spent this month, journal written. |  |
| PASS | PD-13 | Spent-this-month in the header equals the sum of this month's expense entries (including recurring occurrences). |  |
| PASS | PD-14 | Journal tiles (entries, streak, words, average mood) are derived from stored entries. |  |
| PASS | PD-15 | Day roll-over: when midnight passes the app re-renders so "today" moves on without a reload. |  |
| PASS | PD-16 | Derived habit figures (streaks, completion, statistics) update immediately after ticking a habit. |  |
