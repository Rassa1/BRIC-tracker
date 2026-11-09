# BRIC tracker

Logs how crowded the 3rd floor of Cal Poly Pomona's BRIC is, every 30 minutes,
so you can find the emptiest times to go.

## How it works

- **`track.py`** reads the same data as the ASI
  [Live Facility Counts](https://asi.cpp.edu/calendars-hours/live-calendars/) widget,
  but from the JSON API behind it
  (`goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount`), and appends
  one row to `data.csv`. Python standard library only.
- **`.github/workflows/track.yml`** runs `track.py` every 30 minutes on GitHub Actions
  (and on demand from the Actions tab → *Log 3rd floor count* → *Run workflow*), then
  commits `data.csv` back to the repo.
- **`analyze.py`** turns `data.csv` into `heatmap.png` and prints the 5 emptiest slots.

The site reports the 3rd floor as four zones (South, Northeast, North, West, 70 each).
`count` / `capacity` / `percent` are the 3rd-floor **total** (capacity 280); the
per-zone counts are in their own columns.

### data.csv columns

| column | meaning |
|---|---|
| `time`, `weekday`, `hour` | when the row was logged (America/Los_Angeles) |
| `count`, `capacity`, `percent` | 3rd-floor total |
| `status` | `open` unless every 3rd-floor zone is marked closed |
| `source_last_updated` | when staff last submitted the count (Pacific time) |
| `south`, `northeast`, `north`, `west` | per-zone counts |
| `note` | blank normally; an error message if the fetch or parse failed |

If a run can't find the 3rd floor, it still logs a row (with the error in `note`)
and saves the raw response to `latest.html` for debugging. The next successful run
deletes `latest.html`, so if that file exists in the repo, the last run failed.

**Counts are manual headcounts, not live sensors.** The number only changes when
staff submit a new count, and the last count of the night stays up (marked "open")
until morning. `analyze.py` therefore uses each distinct headcount once, at the
time it was taken (`source_last_updated`), so overnight repeats don't skew the averages.

## Run the analysis

First time (needs the [GitHub CLI](https://cli.github.com/) and Python):

```bash
gh repo clone Rassa1/BRIC-tracker   # makes a BRIC-tracker folder
cd BRIC-tracker                     # analyze.py lives in here
pip install matplotlib
python analyze.py                   # writes heatmap.png, prints the 5 emptiest slots
```

After that, open a terminal **inside the `BRIC-tracker` folder** and run:

```bash
git pull                            # get the latest data
python analyze.py
python analyze.py --min-samples 3   # only trust slots seen at least 3 times
```

If you get `can't open file ... analyze.py`, you're in the wrong folder: `cd BRIC-tracker` first.

Give it a couple of weeks before trusting the rankings. Early on, most slots
have just one headcount behind them (shown as `n=`).

## Notes

- GitHub's scheduler often runs late (5–20 minutes) and occasionally skips a run.
  That's fine for averages.
- GitHub can pause scheduled workflows in repos with no activity for 60 days. If
  rows stop appearing, re-enable it under **Actions → Log 3rd floor count**.
