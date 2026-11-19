# GreenLight NYC v2

Tools for analyzing NYC permit timelines for small businesses.

**Status:** early setup. Nothing is built yet.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run greenlight-nyc-v2
```

## Data

Raw downloads go in `data/raw/`. That folder is ignored by git and is never committed.

Secrets go in `.env`, which is also ignored by git.
