"""Download DOB NOW: Build job filings from NYC Open Data for slice 1.

Makes two pulls from the "DOB NOW: Build - Job Application Filings" dataset
(Socrata ID w9ak-ipjd), both covering the same 12-month window:

1. Filings whose FIRST PERMIT was issued in the window (the main analysis).
2. Filings that were FILED in the window (used only to show how many are
   still waiting for a permit).

Only timing and category columns are downloaded: no names or addresses.
Files are saved to data/raw/ (ignored by git), with a manifest that records
exactly what was asked for and what came back.

Run:  python -m uv run python -m greenlight_nyc_v2.fetch [--end YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATASET_ID = "w9ak-ipjd"
DATASET_NAME = "DOB NOW: Build - Job Application Filings"
BASE = "https://data.cityofnewyork.us"
RESOURCE_URL = f"{BASE}/resource/{DATASET_ID}"
METADATA_URL = f"{BASE}/api/views/{DATASET_ID}.json"

COLUMNS = [
    "job_filing_number",
    "job_type",
    "borough",
    "filing_status",
    "filing_review_type",
    "filing_date",
    "approved_date",
    "first_permit_date",
    "current_status_date",
]

PAGE_SIZE = 50_000
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
USER_AGENT = "greenlight-nyc-v2 (https://github.com/JBellissimo/greenlight-nyc-v2)"


def _get(url: str, params: dict[str, str], retries: int = 3) -> bytes:
    """GET a URL with query parameters, retrying briefly on network errors."""
    full = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return resp.read()
        except OSError as err:
            if attempt == retries:
                raise
            print(f"  request failed ({err}); retrying in {5 * attempt}s", file=sys.stderr)
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def window_for(end: date) -> tuple[date, date]:
    """Return (start, end_exclusive) for the 12 months ending on `end` (inclusive)."""
    end_exclusive = end + timedelta(days=1)
    try:
        start = end_exclusive.replace(year=end_exclusive.year - 1)
    except ValueError:  # Feb 29
        start = end_exclusive.replace(year=end_exclusive.year - 1, day=28)
    return start, end_exclusive


def server_count(where: str) -> int:
    body = _get(f"{RESOURCE_URL}.json", {"$select": "count(*) AS n", "$where": where})
    return int(json.loads(body)[0]["n"])


def fetch_to_csv(where: str, out_path: Path) -> int:
    """Download every row matching `where` into out_path, page by page."""
    rows_written = 0
    offset = 0
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        while True:
            params = {
                "$select": ",".join(COLUMNS),
                "$where": where,
                "$order": ":id",
                "$limit": str(PAGE_SIZE),
                "$offset": str(offset),
            }
            text = _get(f"{RESOURCE_URL}.csv", params).decode("utf-8")
            reader = csv.reader(io.StringIO(text))
            header = next(reader, None)
            if header != COLUMNS:
                raise RuntimeError(f"Unexpected columns from server: {header}")
            page = list(reader)
            writer.writerows(page)
            rows_written += len(page)
            print(f"  {out_path.name}: {rows_written:,} rows")
            if len(page) < PAGE_SIZE:
                return rows_written
            offset += PAGE_SIZE


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help="Last day of the 12-month window, inclusive (default: yesterday).",
    )
    args = parser.parse_args(argv)
    start, end_exclusive = window_for(args.end)
    span = f"{start.isoformat()}_{args.end.isoformat()}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    meta = json.loads(_get(METADATA_URL, {}))
    dataset_updated = datetime.fromtimestamp(meta["rowsUpdatedAt"], tz=timezone.utc)

    pulls = {
        "first_permit": "first_permit_date",
        "filed": "filing_date",
    }
    manifest: dict = {
        "dataset_id": DATASET_ID,
        "dataset_name": DATASET_NAME,
        "dataset_rows_updated_at_utc": dataset_updated.isoformat(),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_start": start.isoformat(),
        "window_end_inclusive": args.end.isoformat(),
        "columns": COLUMNS,
        "pulls": {},
    }

    for name, date_col in pulls.items():
        where = (
            f"{date_col} >= '{start.isoformat()}' "
            f"AND {date_col} < '{end_exclusive.isoformat()}'"
        )
        out_path = RAW_DIR / f"filings_{name}_{span}.csv"
        print(f"Pull '{name}': {where}")
        expected = server_count(where)
        written = fetch_to_csv(where, out_path)
        if written != expected:
            raise RuntimeError(
                f"Row count mismatch for '{name}': server says {expected:,}, saved {written:,}"
            )
        manifest["pulls"][name] = {
            "where": where,
            "file": out_path.name,
            "rows": written,
            "server_count": expected,
        }

    manifest_path = RAW_DIR / "fetch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Done. Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
