# Habits, planner, budget and journal

A single-file web app (`index.html`) with a habit tracker, planner, budget tracker and journal (hourly mood with an emotion wheel, weight and calorie tracking). No build step, no server, no dependencies.

Data is saved in your browser (localStorage) and can be exported or imported as JSON from the menu. Nothing is sent to any server, apart from public exchange-rate lookups.

Version 0.2

## Host on GitHub Pages

1. Create a new repository on GitHub (for example `habits`).
2. Upload everything in this folder (keep `.github` and `.nojekyll`), or push it with git:
   ```
   git init && git add . && git commit -m "v0.1"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. In the repository go to Settings, then Pages, and set Source to "GitHub Actions". The included workflow publishes the site on each push to `main`.
4. Your app will be at `https://<you>.github.io/<repo>/`.

On iPhone, open the link in Safari, tap Share, then "Add to Home Screen".

## Requirements and tests

- `REQUIREMENTS.md` lists every requirement with an ID (115 of them: platform, data, resizing, habits, planner, budget, journal, passive data such as the clock, timer and exchange rates).
- `tests/validate_requirements.py` checks each one in a real browser and writes a pass / fail report to `tests/report/report.html` (also `report.md` and `results.json`).
- `tests/TEST_HISTORY.md` records every test done since the first build; `tests/legacy/` keeps the original scripts.

```
pip install playwright && playwright install chromium
python tests/validate_requirements.py            # all requirements
python tests/validate_requirements.py --only BUD,PD-0   # a group, or IDs by prefix
```

## Files

- `index.html` – the whole app
- `.github/workflows/pages.yml` – deploys only `index.html` to GitHub Pages
- `CHANGELOG.md` – what changed in each version
- `.nojekyll`, `.gitignore` – Pages and git housekeeping
- `REQUIREMENTS.md`, `tests/` – requirements and the Playwright validator
- `LICENSE` – MIT
