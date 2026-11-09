#!/usr/bin/env python3
"""Find the emptiest times on the BRIC 3rd floor.

Reads data.csv, saves heatmap.png (average crowding by day x hour, open hours
only) and prints the 5 emptiest time slots.

    pip install matplotlib
    python analyze.py
    python analyze.py --min-samples 3   # ignore slots seen fewer than 3 times
"""

import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Single-hue sequential ramp (light = empty, dark = packed) and neutral inks
RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"


def fmt_hour(h):
    h %= 24
    return "12a" if h == 0 else "12p" if h == 12 else f"{h}a" if h < 12 else f"{h - 12}p"


def load_headcounts(path):
    """One observation per staff headcount, placed at the time it was taken.

    The source only changes when staff submit a new count, so consecutive
    30-minute polls often repeat the same number - including overnight, when the
    last count of the night sits there (still marked open) until morning.
    Keying on source_last_updated collapses those repeats into one reading.
    """
    obs = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("status") != "open":
                continue
            try:
                taken = datetime.strptime(r["source_last_updated"], "%Y-%m-%d %H:%M")
                obs[taken] = (int(r["count"]), float(r["percent"]))
            except (KeyError, TypeError, ValueError):
                continue  # error rows / blanks
    return obs


def by_slot(obs):
    """{(weekday, hour): (avg_count, avg_percent, n)}"""
    groups = defaultdict(list)
    for taken, cp in obs.items():
        groups[(taken.weekday(), taken.hour)].append(cp)
    return {k: (sum(c for c, _ in v) / len(v), sum(p for _, p in v) / len(v), len(v))
            for k, v in groups.items()}


def heatmap(slots, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        print("matplotlib not installed, skipping heatmap  ->  pip install matplotlib")
        return

    hours = list(range(min(h for _, h in slots), max(h for _, h in slots) + 1))
    nan = float("nan")
    grid = [[slots[(d, h)][1] if (d, h) in slots else nan for h in hours] for d in range(7)]
    vmax = max(5.0, max(p for _, p, _ in slots.values()))

    cmap = LinearSegmentedColormap.from_list("crowd", RAMP)
    cmap.set_bad(SURFACE)
    fig, ax = plt.subplots(figsize=(max(6.5, 0.5 * len(hours) + 2.5), 4.4), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    mesh = ax.pcolormesh(grid, cmap=cmap, vmin=0, vmax=vmax,  # NaN -> blank cell
                         edgecolors=SURFACE, linewidth=2)
    ax.invert_yaxis()

    for d in range(7):
        for i, h in enumerate(hours):
            if (d, h) in slots:
                count, pct, _ = slots[(d, h)]
                ax.text(i + 0.5, d + 0.5, f"{count:.0f}", ha="center", va="center",
                        fontsize=8, color="white" if pct / vmax > 0.55 else INK)

    ax.set_xticks([i + 0.5 for i in range(len(hours))], [fmt_hour(h) for h in hours])
    ax.set_yticks([d + 0.5 for d in range(7)], [d[:3] for d in DAYS])
    ax.tick_params(length=0, colors=INK_2, labelsize=9)
    for s in ax.spines.values():
        s.set_visible(False)

    cb = fig.colorbar(mesh, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("avg % of capacity", color=INK_2, fontsize=9)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=INK_2, length=0, labelsize=8)

    ax.set_title("BRIC 3rd floor: how crowded, by day and hour", loc="left",
                 color=INK, fontsize=12, pad=22)
    ax.text(0, 1.02, "Cell number = average people. Blank = no headcount yet.",
            transform=ax.transAxes, color=INK_2, fontsize=8.5, va="bottom")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Saved heatmap -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", default=os.path.join(HERE, "data.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "heatmap.png"))
    ap.add_argument("--min-samples", type=int, default=1,
                    help="only rank slots with at least this many headcounts (default 1)")
    args = ap.parse_args()

    obs = load_headcounts(args.csv)
    if not obs:
        print("No open-hours headcounts in", args.csv, "yet - let the tracker run for a while.")
        return
    first, last = min(obs), max(obs)
    print(f"{len(obs)} distinct headcounts from {first:%a %b %d} to {last:%a %b %d}\n")

    slots = by_slot(obs)
    heatmap(slots, args.out)

    ranked = sorted((kv for kv in slots.items() if kv[1][2] >= args.min_samples),
                    key=lambda kv: (kv[1][1], kv[1][0]))
    print(f"\n5 emptiest time slots (needs >= {args.min_samples} headcount(s) per slot):")
    for (d, h), (count, pct, n) in ranked[:5]:
        print(f"  {DAYS[d]:<9}  {fmt_hour(h):>3}-{fmt_hour(h + 1):<3}  "
              f"avg {count:4.1f} people  ({pct:4.1f}%)   n={n}")
    if not ranked:
        print("  (none yet - lower --min-samples or collect more data)")


if __name__ == "__main__":
    main()
