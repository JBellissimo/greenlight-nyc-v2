"""Slice 1 analysis: how long DOB NOW jobs take to reach their first permit.

Reads the files saved by fetch.py and writes three files to outputs/:

- slice1_durations.csv     median, 90th percentile (p90), mean and count of
                           days for three measures, by job type and borough:
                             total          filing date -> first permit date
                             review         filing date -> approval date
                             post_approval  approval date -> first permit date
- slice1_still_waiting.csv share of jobs filed in the same window that have
                           no permit yet (context, not a wait time)
- slice1_route_gap.csv      Professional Certification vs Standard Plan
                           Examination within each job type, and with the
                           job-type mix held equal (selection-bias check)
- slice1_run_metadata.json what data went in, every filter and how many rows
                           it removed, and the git commit of this script

Cohort: initial filings (job filing number ending in -I<n>) whose first permit
was issued in the window. Subsequent filings (-S), amendments (-P) and other
document types are excluded, as is job type "No Work" (it never gets a permit).
All durations are calendar days between the date parts of the timestamps.
Results are broken down by job type, borough and review route (Standard Plan
Examination vs Professional Certification).

Run:  python -m uv run python -m greenlight_nyc_v2.analyze
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "outputs"
LOW_N = 30

MEASURES = {
    "total": ("filing_date", "first_permit_date"),
    "review": ("filing_date", "approved_date"),
    "post_approval": ("approved_date", "first_permit_date"),
}
DATE_COLS = ["filing_date", "approved_date", "first_permit_date", "current_status_date"]

# Each output row summarizes one group. "review_route" is the DOB NOW
# filing_review_type: Standard Plan Examination (DOB examiners review the plans)
# or Professional Certification (the architect/engineer self-certifies them).
GROUPINGS = {
    "citywide": [],
    "job_type": ["job_type"],
    "borough": ["borough"],
    "review_route": ["review_route"],
    "job_type_x_borough": ["job_type", "borough"],
    "job_type_x_review_route": ["job_type", "review_route"],
}
LABELS = ["job_type", "borough", "review_route"]


def git_version() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    for col in DATE_COLS:
        # Keep the calendar date only: durations are whole calendar days.
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()
    df["doc_type"] = df["job_filing_number"].str.extract(r"-([A-Z])\d+$")[0]
    df["review_route"] = df["filing_review_type"].fillna("Unknown")
    return df


def grouped(df: pd.DataFrame):
    """Yield (level, labels, rows) for every group in GROUPINGS."""
    for level, keys in GROUPINGS.items():
        groups = [((), df)] if not keys else df.groupby(keys)
        for key, g in groups:
            key = key if isinstance(key, tuple) else (key,)
            found = dict(zip(keys, key))
            yield level, {c: found.get(c, "All") for c in LABELS}, g


def apply_filters(df: pd.DataFrame, log: list[dict]) -> pd.DataFrame:
    """Apply the cohort filters, recording how many rows each one removes."""

    def step(name: str, keep: pd.Series) -> None:
        nonlocal df
        removed = int((~keep).sum())
        df = df[keep]
        log.append({"filter": name, "removed": removed, "remaining": len(df)})

    log.append({"filter": "rows downloaded", "removed": 0, "remaining": len(df)})
    step("keep initial filings only (-I); drop -S, -P and other document types",
         df["doc_type"].eq("I"))
    step("drop job type 'No Work'", df["job_type"].ne("No Work"))
    # A few filing numbers appear twice; keep the most recently updated row.
    df = df.sort_values("current_status_date")
    step("drop duplicate job filing numbers (keep most recently updated)",
         ~df["job_filing_number"].duplicated(keep="last"))
    step("drop rows missing a filing date", df["filing_date"].notna())
    return df


def add_durations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for name, (start, end) in MEASURES.items():
        df[name] = (df[end] - df[start]).dt.days
    return df


def summarize(df: pd.DataFrame, log: list[dict]) -> pd.DataFrame:
    rows = []
    for measure in MEASURES:
        values = df[[*LABELS, measure]].dropna(subset=[measure])
        negative = values[measure] < 0
        log.append({
            "filter": f"{measure}: rows without the needed dates",
            "removed": int(df[measure].isna().sum()),
            "remaining": len(values),
        })
        log.append({
            "filter": f"{measure}: rows with negative days (end before start)",
            "removed": int(negative.sum()),
            "remaining": int((~negative).sum()),
        })
        values = values[~negative]
        for level, labels, g in grouped(values):
            s = g[measure]
            rows.append({
                "measure": measure,
                "level": level,
                **labels,
                "n": len(s),
                "median_days": round(float(s.median()), 1),
                "p90_days": round(float(s.quantile(0.9)), 1),
                "mean_days": round(float(s.mean()), 1),
                "low_n": len(s) < LOW_N,
            })
    return pd.DataFrame(rows)


def weighted_quantile(values: pd.Series, weights: pd.Series, q: float) -> float:
    """Quantile of `values` where each row counts `weights` times (step method)."""
    order = values.argsort(kind="stable")
    v = values.to_numpy()[order]
    w = weights.to_numpy()[order]
    cum = w.cumsum()
    return float(v[(cum >= q * cum[-1]).argmax()])


def route_gap(df: pd.DataFrame) -> pd.DataFrame:
    """Compare the two review routes within each job type, then overall.

    The overall route gap mixes two things: the route itself, and the fact that
    the routes handle different kinds of jobs. Holding job type constant
    removes the second part (but not other differences, such as job size).

    The "same job mix" rows reweight one route's jobs so its job-type mix
    matches the other route's, then recompute the median and p90.
    """
    pc_name, spe_name = "Professional Certification", "Standard Plan Examination"
    total = df.dropna(subset=["total"])
    total = total[total["total"] >= 0]
    rows = []

    def stats(s: pd.Series, w: pd.Series | None = None) -> dict:
        if w is None:
            return {"n": len(s), "median": float(s.median()), "p90": float(s.quantile(0.9))}
        return {"n": int((w > 0).sum()), "median": weighted_quantile(s, w, 0.5),
                "p90": weighted_quantile(s, w, 0.9)}

    def add(comparison: str, job_type: str, pc: dict, spe: dict) -> None:
        rows.append({
            "comparison": comparison,
            "job_type": job_type,
            "pc_n": pc["n"], "pc_median_days": round(pc["median"], 1),
            "pc_p90_days": round(pc["p90"], 1),
            "spe_n": spe["n"], "spe_median_days": round(spe["median"], 1),
            "spe_p90_days": round(spe["p90"], 1),
            "median_gap_days": round(spe["median"] - pc["median"], 1),
            "low_n": min(pc["n"], spe["n"]) < LOW_N,
        })

    pc_all = total[total["review_route"] == pc_name]
    spe_all = total[total["review_route"] == spe_name]
    add("unadjusted (all job types pooled)", "All", stats(pc_all["total"]), stats(spe_all["total"]))

    for job_type, g in total.groupby("job_type"):
        pc = g[g["review_route"] == pc_name]["total"]
        spe = g[g["review_route"] == spe_name]["total"]
        if len(pc) and len(spe):
            add("within job type", job_type, stats(pc), stats(spe))
        else:
            only = pc_name if len(pc) else spe_name
            rows.append({"comparison": f"within job type (only {only} jobs)",
                         "job_type": job_type, "pc_n": len(pc), "spe_n": len(spe)})

    # Reweight so both routes have the same job-type mix. Job types handled by
    # only one route get weight 0, since there is nothing to compare them with.
    pc_mix = pc_all["job_type"].value_counts(normalize=True)
    spe_mix = spe_all["job_type"].value_counts(normalize=True)
    shared = pc_mix.index.intersection(spe_mix.index)
    spe_w = spe_all["job_type"].map((pc_mix / spe_mix).reindex(shared)).fillna(0)
    pc_w_shared = pc_all["job_type"].isin(shared).astype(float)
    add("same job mix: Standard Plan Exam reweighted to Prof. Cert.'s mix", "All (shared types)",
        stats(pc_all["total"], pc_w_shared), stats(spe_all["total"], spe_w))
    pc_w = pc_all["job_type"].map((spe_mix / pc_mix).reindex(shared)).fillna(0)
    spe_w_shared = spe_all["job_type"].isin(shared).astype(float)
    add("same job mix: Prof. Cert. reweighted to Standard Plan Exam's mix", "All (shared types)",
        stats(pc_all["total"], pc_w), stats(spe_all["total"], spe_w_shared))
    return pd.DataFrame(rows)


def still_waiting(df: pd.DataFrame, window_end: pd.Timestamp) -> pd.DataFrame:
    """Share of jobs filed in the window that have no first permit yet."""
    df = df.copy()
    df["waiting"] = df["first_permit_date"].isna()
    six_months_before_end = window_end - pd.DateOffset(months=6)
    df["filed_6mo_plus_ago"] = df["filing_date"] <= six_months_before_end
    rows = []
    for level, labels, g in grouped(df):
        older = g[g["filed_6mo_plus_ago"]]
        rows.append({
            "level": level,
            **labels,
            "filed": len(g),
            "no_permit_yet": int(g["waiting"].sum()),
            "share_no_permit_yet": round(float(g["waiting"].mean()), 3),
            "filed_6mo_plus_ago": len(older),
            "share_no_permit_yet_if_filed_6mo_plus_ago": (
                round(float(older["waiting"].mean()), 3) if len(older) else None
            ),
            "low_n": len(g) < LOW_N,
        })
    return pd.DataFrame(rows)


def main() -> None:
    manifest = json.loads((RAW_DIR / "fetch_manifest.json").read_text(encoding="utf-8"))
    window_end = pd.Timestamp(manifest["window_end_inclusive"])
    OUT_DIR.mkdir(exist_ok=True)

    permit_log: list[dict] = []
    cohort = apply_filters(load(RAW_DIR / manifest["pulls"]["first_permit"]["file"]), permit_log)
    cohort = add_durations(cohort)
    durations = summarize(cohort, permit_log)

    # Context for the medians: how long ago were these jobs filed?
    filed_over_1yr_before_permit = int((cohort["total"] > 365).sum())

    waiting_log: list[dict] = []
    filed = apply_filters(load(RAW_DIR / manifest["pulls"]["filed"]["file"]), waiting_log)
    waiting = still_waiting(filed, window_end)

    sort_cols = ["level", *LABELS]
    durations.sort_values(["measure", *sort_cols]).to_csv(
        OUT_DIR / "slice1_durations.csv", index=False, lineterminator="\n")
    waiting.sort_values(sort_cols).to_csv(
        OUT_DIR / "slice1_still_waiting.csv", index=False, lineterminator="\n")
    route_gap(cohort).to_csv(
        OUT_DIR / "slice1_route_gap.csv", index=False, lineterminator="\n")

    metadata = {
        "script": "src/greenlight_nyc_v2/analyze.py",
        "script_git_version": git_version(),
        "source": {k: manifest[k] for k in (
            "dataset_id", "dataset_name", "dataset_rows_updated_at_utc",
            "fetched_at_utc", "window_start", "window_end_inclusive")},
        "source_pulls": manifest["pulls"],
        "definitions": {
            "cohort": "Initial (-I) DOB NOW: Build filings, excluding job type 'No Work', "
                      "whose first_permit_date falls in the window.",
            "days": "Calendar days between the date parts of the two timestamps.",
            "total": "filing_date -> first_permit_date",
            "review": "filing_date -> approved_date (plan approval). Professional "
                      "Certification jobs sometimes have no approved_date, so they are "
                      "under-represented in review and post_approval.",
            "review_route": "filing_review_type: Standard Plan Examination or "
                            "Professional Certification.",
            "post_approval": "approved_date -> first_permit_date",
            "p90": "90th percentile (linear interpolation): 9 in 10 jobs took this long or less.",
            "low_n": f"Fewer than {LOW_N} jobs in the group; treat as unreliable.",
            "still_waiting": "Initial filings filed in the window, excluding 'No Work', "
                             "with no first_permit_date as of the download.",
        },
        "cohort_filters": permit_log,
        "cohort_jobs_with_total_over_365_days": filed_over_1yr_before_permit,
        "still_waiting_filters": waiting_log,
    }
    (OUT_DIR / "slice1_run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    city = durations[(durations["level"] == "citywide")]
    print(city[["measure", "n", "median_days", "p90_days", "mean_days"]].to_string(index=False))
    print(f"Wrote {OUT_DIR / 'slice1_durations.csv'}")
    print(f"Wrote {OUT_DIR / 'slice1_still_waiting.csv'}")
    print(f"Wrote {OUT_DIR / 'slice1_route_gap.csv'}")
    print(f"Wrote {OUT_DIR / 'slice1_run_metadata.json'}")


if __name__ == "__main__":
    main()
