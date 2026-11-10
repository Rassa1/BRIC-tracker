# BRIC tracker

Logs how crowded the 3rd floor of Cal Poly Pomona's BRIC is, every 30 minutes,
so you can find the emptiest times to go.

## How it works

- **`track.py`** reads the same data as the ASI
  [Live Facility Counts](https://asi.cpp.edu/calendars-hours/live-calendars/) widget,
  but from the JSON API behind it
  (`goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount`), and appends
  one row to `data.csv`. Python standard library only.
- **`.github/workflows/track.yml`** runs `track.py` on GitHub Actions, then commits
  `data.csv` back to the repo. A free [cron-job.org](https://cron-job.org) job starts
  it every 30 minutes (see *Timer* below). You can also start it by hand from the Actions
  tab → *Log 3rd floor count* → *Run workflow*.
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

## Timer

GitHub's built-in `schedule` trigger is unreliable for this: on the first day it
started only 2 of about 32 runs. The real timer is a cron-job.org job that calls
GitHub's "run workflow" API every 30 minutes:

- `POST https://api.github.com/repos/Rassa1/BRIC-tracker/actions/workflows/track.yml/dispatches`
  with body `{"ref":"main"}` and a fine-grained token limited to this repo with
  only **Actions: Read and write**.
- GitHub's own schedule stays in the workflow as a backup. Extra rows are harmless,
  because `analyze.py` counts each headcount once.

**The token expires on 2027-02-08.** Before then, regenerate it at
github.com/settings/personal-access-tokens (open *bric-tracker-cron* → *Regenerate*)
and paste the new value into the cron-job.org job's `Authorization: Bearer …` header.
If cron-job.org starts emailing you about failed runs, this is the likely reason.
