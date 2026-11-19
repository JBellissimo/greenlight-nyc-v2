# GreenLight NYC v2

## Goal
Find where NYC permit time actually goes, then decide by Nov 25, 2026
whether to build a pre-audit agent or a delay tracker.

## Rules
- Python + uv. Run uv as `python -m uv` (standalone uv isn't installed yet).
- Raw data lives in data/raw/ and is never committed.
- Every number in outputs/ must trace to a script in src/.
- Explain each step to me as a beginner: what you did and why.
- Small commits with clear messages.

## Definition of done (slice 1)
A reproducible script that outputs median days from filing to permit,
by job type and borough, for the last 12 months.
