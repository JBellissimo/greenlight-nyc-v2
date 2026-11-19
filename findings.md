# Slice 1 findings: how long NYC jobs take to get their first permit

*Data: DOB NOW: Build – Job Application Filings (NYC Open Data `w9ak-ipjd`), downloaded 2026-11-19. The dataset was last updated 2026-11-18.*
*Every number from our data comes from [`outputs/`](outputs/), produced by [`src/greenlight_nyc_v2/analyze.py`](src/greenlight_nyc_v2/analyze.py). City figures link to their source and page.*

## The short version

- **The typical job got its first permit 21 days after filing**, measured as the median across 60,386 jobs. But 1 in 10 took **301 days or more**, so the wait is very uneven.
- **The biggest factor is the review route, not the job type or the borough.**
  - **Professional Certification:** the architect or engineer certifies the plans themselves. The median is **7 days**.
  - **Standard Plan Examination:** a DOB examiner reviews the plans. The median is **103 days**, and the 90th percentile is **556 days**.
  - Most of this gap remains when you compare jobs of the same type. Section 8 shows that 75–94% of it survives. That still doesn't prove the route *causes* the difference.
- **Big jobs take much longer.** The median is 294 days for New Buildings and 216 days for Alteration CO (major renovations), versus 16 days for Alterations.
- **For Standard Plan Examination jobs, the time splits roughly in half.** About half is getting plans approved (median 36 days). The other half is getting from approval to a permit (median 34 days).
- **The city says most pre-approval time is the applicant fixing problems.** In its own words: *"time with the applicant is typically three times as long as the time the filing is with the Department for review"* ([MMR FY2026, p. 357–358](https://www.nyc.gov/assets/operations/downloads/pdf/mmr2026/dob.pdf)).
- **No public data counts objections per job**, so we can't report a median objection count. Section 5 explains.

## 1. What we measured, and how

**The question:** for jobs that got their first DOB permit in the last 12 months (2025-11-19 to 2026-11-18), how many calendar days passed between filing and that permit?

**Why we start from the permit date:** about 29% of jobs filed in the last year don't have a permit yet (section 4). Starting from the filing date would quietly leave out the slow jobs still waiting. Starting from the permit date means every job in the group has a finished wait. The trade-off is that the group includes some old jobs: **4,825 of them were filed more than a year before their permit**. That's why the 90th percentiles are so high. Slice 2 will use survival analysis to handle unfinished jobs properly.

**Three measures** (calendar days, weekends included):

| Measure | From → to | What it captures |
|---|---|---|
| **Total** | filing → first permit | The whole wait |
| **Review** | filing → plan approval | DOB review time plus applicant correction time (the data can't separate them) |
| **Post-approval** | plan approval → first permit | Paperwork after approval, such as insurance and contractor sign-up. It can also include owners choosing to wait. |

**Filters.** Each step's count is recorded in [`outputs/slice1_run_metadata.json`](outputs/slice1_run_metadata.json):

| Step | Rows removed | Rows left |
|---|---:|---:|
| Filings whose first permit was issued in the window | n/a | 90,778 |
| Keep only *initial* filings (number ends in `-I1`, `-I2`, …). Drop subsequent filings (`-S`), amendments (`-P`) and others, because they're add-ons to a job, not a new job. | 30,391 | 60,387 |
| Drop job type "No Work" (never gets a permit) | 0 | 60,387 |
| Drop duplicate filing numbers | 0 | 60,387 |
| Drop rows with no filing date | 1 | **60,386** |

For *review* and *post-approval*, a further **8,323 jobs have no approval date**. All of them are Professional Certification Alterations, so those two measures cover 52,063 jobs. Three post-approval rows where the permit date came before the approval date were also dropped.

**How to read the tables:**
- **Median:** half of jobs were faster and half were slower.
- **90th percentile (p90):** 9 in 10 jobs took this long or less, so it shows the slow tail.
- **n:** the number of jobs in the group.
- **Low n:** groups with fewer than 30 jobs are marked ⚠ and shouldn't be trusted.

## 2. Results

### By review route (the biggest factor)

| Review route | Jobs | Total: median / p90 | Review: median / p90 | Post-approval: median / p90 |
|---|---:|---:|---:|---:|
| Professional Certification | 36,834 | **7** / 85 | 1 / 5 | 8 / 105 |
| Standard Plan Examination | 23,552 | **103** / 556 | 36 / 196 | 34 / 384 |
| **All jobs** | **60,386** | **21** / 301 | 5 / 104 | 14 / 229 |

### By job type

| Job type | Jobs | Total: median / p90 | Review: median / p90 | Post-approval: median / p90 |
|---|---:|---:|---:|---:|
| Alteration (minor renovation) | 55,470 | 16 / 231 | 4 / 63 | 12 / 207 |
| Alteration CO (major renovation) | 1,781 | 216 / 663 | 134 / 371 | 39.5 / 353 |
| ALT-CO – New Building with Existing Elements | 419 | 259 / 613 | 180 / 413 | 49 / 268 |
| Full Demolition | 1,316 | 156.5 / 425 | 47 / 153 | 82 / 344 |
| New Building | 1,400 | 294 / 944 | 172 / 546 | 81.5 / 496 |

### By job type and review route

| Job type | Route | Jobs | Total: median / p90 | Review: median | Post-approval: median |
|---|---|---:|---:|---:|---:|
| Alteration | Prof. Certification | 36,453 | 7 / 80 | 1 | 7 |
| Alteration | Standard Plan Exam | 19,017 | 79 / 505 | 28 | 28 |
| Alteration CO | Prof. Certification | 152 | 99.5 / 361 | 45 | 26 |
| Alteration CO | Standard Plan Exam | 1,629 | 228 / 679 | 145 | 40.5 |
| ALT-CO – NB w/ Existing Elements | Prof. Certification | 10 ⚠ | 112 / 535 | 81.5 | 48 |
| ALT-CO – NB w/ Existing Elements | Standard Plan Exam | 409 | 260 / 613 | 182 | 49 |
| Full Demolition | Standard Plan Exam | 1,316 | 156.5 / 425 | 47 | 82 |
| New Building | Prof. Certification | 219 | 97 / 894 | 53 | 26 |
| New Building | Standard Plan Exam | 1,181 | 315 / 979 | 187 | 91 |

### By job type and borough (total days: median / p90, number of jobs)

| Job type | Bronx | Brooklyn | Manhattan | Queens | Staten Island |
|---|---|---|---|---|---|
| Alteration | 14 / 289 (5,273) | 16 / 284 (13,219) | 17 / 172 (23,701) | 15 / 278 (10,382) | 13 / 319 (2,895) |
| Alteration CO | 269.5 / 705 (154) | 225 / 725 (553) | 207 / 540 (407) | 202 / 642 (550) | 208 / 885 (117) |
| ALT-CO – NB w/ Existing Elements | 352.5 / 977 (12 ⚠) | 297 / 607 (168) | 323 / 597 (11 ⚠) | 227.5 / 546 (202) | 250.5 / 883 (26 ⚠) |
| Full Demolition | 156 / 402 (209) | 166 / 442 (391) | 256 / 473 (95) | 168 / 498 (428) | 81 / 217 (193) |
| New Building | 334 / 791 (223) | 357 / 1,242 (297) | 453 / 1,171 (45) | 315 / 876 (407) | 164 / 894 (428) |
| **All job types** | 21 / 386 (5,871) | 23 / 357 (14,628) | 18 / 194 (24,259) | 26 / 367 (11,969) | 32 / 404 (3,659) |

Borough differences are small next to job-type and review-route differences. Manhattan's slow tail is the shortest, and its 90th percentile of 194 days is the lowest. Staten Island New Buildings are much faster than New Buildings elsewhere.

## 3. Where the time goes

- **Professional Certification jobs barely wait for approval.** The median review is 1 day, because the professional's certification stands in for DOB review. Their remaining wait, a median of 8 days, comes after approval.
- **Standard Plan Examination jobs wait at both stages.** For Alterations it's a median of 28 days to approval and 28 more to a permit. For New Buildings it's 187 days to approval, then 91 days to a permit.
- **DOB's own review is only a small part of the review stage.** The city reports DOB takes 4.4 to 9.4 days on average for its *first* look at a plan (section 6). Our review medians for big jobs are 134 to 187 days. The difference is resubmission rounds and, according to the city, mostly the applicant's time making corrections. These datasets can't separate the two.
- **The post-approval stage is surprisingly large and has a long tail.** For Standard Plan Examination jobs the 90th percentile is 384 days. We don't know yet how much of this is real delay (insurance, contractor registration, other agencies) and how much is owners choosing to wait before pulling a permit.

## 4. Jobs still waiting (why these medians are a floor)

We looked at initial filings *filed* in the same 12 months, excluding No Work: 66,319 jobs. Here's how many have no permit yet. Source: [`outputs/slice1_still_waiting.csv`](outputs/slice1_still_waiting.csv).

| Group | Jobs filed | No permit yet | No permit yet, among those filed 6+ months ago |
|---|---:|---:|---:|
| All | 66,319 | 28.6% | 19.8% |
| Professional Certification | 38,452 | 12.5% | 7.2% |
| Standard Plan Examination | 27,867 | 51.0% | 36.7% |
| New Building | 1,871 | 78.4% | 68.1% |
| Alteration CO | 2,685 | 74.6% | 58.5% |
| Alteration | 59,422 | 23.5% | 15.2% |

Some of these jobs are still moving and some have stalled or been abandoned. The data can't tell which is which. But the slowest current jobs aren't in section 2's medians yet, so real current waits for Standard Plan Examination, New Building and Alteration CO jobs are likely *longer* than reported. Slice 2's survival analysis will measure this properly.

## 5. Objections and review cycles: no per-job data exists

We looked for any field or DOB dataset that records how many objections or review cycles each job had:

- **We checked all 40 Department of Buildings datasets on NYC Open Data**, scanning their column names for objection, cycle, resubmission, review and examiner.
- **DOB NOW: Build – Job Application Filings** (`w9ak-ipjd`) has only each filing's *current* status, for example "Objections". It keeps no history, so it can't show how many rounds a job went through.
- **The only objection fields are in DOB NOW: Build – Elevator Permit Applications** (`kfp4-dz4h`): first objection date, last objection date and resubmission date. These are dates, not counts, and they cover elevator work only.

**So we can't report a median objection count by job type.** The closest public figure is citywide only. In Fiscal 2026, DOB completed **111,842 resubmission plan reviews** alongside **156,389 first plan reviews** for DOB NOW applications ([MMR FY2026, p. 358](https://www.nyc.gov/assets/operations/downloads/pdf/mmr2026/dob.pdf)). By our arithmetic, that's roughly 0.7 resubmission reviews per first review. That suggests correction rounds are common, but it doesn't say which jobs have them.

Getting per-job objection counts would need a records request to DOB, or another source such as expediter or architect data.

## 6. How this compares with NYC's own published numbers

The city publishes **averages** (means) for **fiscal years** (FY2026 = July 2025 to June 2026), for **all DOB NOW applications**, and measures only to **approval**, not to permit. It doesn't publish filing-to-permit times. The closest comparison is our *review* measure, and we report its mean alongside it.

| City figure (source) | City value | Our nearest equivalent |
|---|---|---|
| Average days from filing to approval, all DOB NOW applications ([MMR FY2026, p. 357–358](https://www.nyc.gov/assets/operations/downloads/pdf/mmr2026/dob.pdf)) | **20.3 days** in FY2025 → **25.4 days** in FY2026 | Filing → approval: **mean 40.1, median 5** (all jobs). Standard Plan Examination: mean 83, median 36. Professional Certification: mean 4.6, median 1. |
| Same measure, first 4 months of each fiscal year ([PMMR FY2026, p. 321–322](https://www.nyc.gov/assets/operations/downloads/pdf/pmmr2026/dob.pdf)) | 20.3 → **23.6 days** (Jul–Oct 2025 vs Jul–Oct 2024) | (same as above) |
| Average days for DOB's *first* plan review, DOB NOW ([MMR FY2026, p. 358](https://www.nyc.gov/assets/operations/downloads/pdf/mmr2026/dob.pdf)) | FY2026: New Buildings **9.4**, Major Renovations (Alteration CO) **8.4**, Minor Renovations (Alteration) **4.4**, all applications **5.4**. FY2025: 6.3 / 6.0 / 3.2 / 3.7. | Not measurable: the open data has no first-review date. Our review medians (New Building 172, Alteration CO 134, Alteration 4) include every round plus applicant time. |
| State Comptroller summary ([July 2, 2026 release](https://www.osc.ny.gov/press/releases/2026/07/dinapoli-nyc-department-buildings-meets-critical-goals-lags-lower-priority-issues)) | 2025: first plan review **3.7 business days**, application to approval **20.3 days**. 2020: 1 day and 8.3 days. | Context: the city's own figures show these times rising every year since 2020. |

**Why our numbers differ from the city's:**
1. **Different jobs.** We count only *initial* filings that reached a permit in our window, including old ones: 4,825 were filed over a year earlier. The city counts all DOB NOW applications, including subsequent filings and amendments, which is a different mix of jobs. It also doesn't say whether it counts applications by filing date or by approval date.
2. **Mean vs median.** A few very slow jobs pull the mean far above the median. Our citywide mean is 40.1 days and our median is 5. The city's single average hides how uneven the waits are.
3. **Approval isn't the end.** The city stops counting at approval. Our data shows a median of 14 days more to reach a permit (34 days for Standard Plan Examination jobs), and that stage appears in no city performance indicator we found.
4. **Different time periods.** The city uses fiscal years; we use a rolling year from Nov 2025 to Nov 2026. They overlap by about 7 months.

**Two notes on the city reports:**
- The city revised one figure between reports. FY2025 DOB NOW resubmission reviews appear as 100,023 in the FY2025 MMR (p. 358) and as 106,759 in the FY2026 MMR. The FY2026 preliminary report says previously published resubmission figures were corrected: *"Fiscal 2025 total from 100,023 to 106,759"* ([PMMR FY2026, p. 325](https://www.nyc.gov/assets/operations/downloads/pdf/pmmr2026/dob.pdf)).
- The FY2026 numbers in this file come from the full-year FY2026 MMR. They're newer than the preliminary report's figures.

**The old GreenLight site's claims don't hold up.** It said "the city says 22 work days, reality is 47 calendar days" for "ALT-2" permits. DOB NOW has no ALT-2 job type. The city's published figure is filing to approval (25.4 days in FY2026), not to permit. And the typical Alteration is faster than 47 days (median 16 days total), while Standard Plan Examination Alterations are slower (median 79 days).

## 7. What this means for the Nov 25 decision

What the data supports:
- **Delays are concentrated in specific jobs, not spread across all of them.** About 61% of jobs (Professional Certification) get a permit in about a week. The long waits are Standard Plan Examination jobs, especially New Buildings, Alteration CO and demolitions. Any tool should target those jobs.
- **A pre-audit agent would target the review stage.** That's the median 36 days for Standard Plan Examination jobs, and 134 to 187 days for major renovations and new buildings. The city's own statements say this stage is mostly correction time and that resubmissions are common. That fits a "catch problems before filing" product. But we can't yet show how many objections a typical job gets, or which kinds of objection cost the most time.
- **A delay tracker would cover both stages, including post-approval.** Post-approval is large (median 34 days, p90 384 for Standard Plan Examination), appears in no city performance indicator, and the public data already supports measuring it.

What we still don't know:
- How the review stage splits between DOB time and applicant time for each job.
- How many objection rounds jobs have.
- How much post-approval time is real delay versus owner choice.
- How long the many unfinished jobs will end up taking (slice 2).

## 8. Selection-bias check: is the 7 vs 103 day gap just job mix?

**The worry:** self-certified jobs are mostly simple Alterations, while examiner-reviewed jobs include nearly all New Buildings, major renovations and demolitions. If that were the whole story, the gap would be about job type, not review route.

**The check:** compare the two routes *within the same job type*. Then recompute the overall gap after reweighting one route so its job-type mix matches the other's. Source: [`outputs/slice1_route_gap.csv`](outputs/slice1_route_gap.csv). All figures are total days from filing to first permit.

| Job type | Self-certified: jobs | median | p90 | DOB examiner: jobs | median | p90 | Median gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| Alteration | 36,453 | 7 | 80 | 19,017 | 79 | 505 | **72** |
| Alteration CO | 152 | 99.5 | 361 | 1,629 | 228 | 679 | **128.5** |
| New Building | 219 | 97 | 894 | 1,181 | 315 | 979 | **218** |
| ALT-CO – NB w/ Existing Elements | 10 ⚠ | 112 | 535 | 409 | 260 | 613 | 148 (too few self-certified jobs to trust) |
| Full Demolition | 0 | n/a | n/a | 1,316 | 156.5 | 425 | n/a (no self-certified jobs) |
| **All job types pooled (the original comparison)** | 36,834 | 7 | 85 | 23,552 | 103 | 556 | **96** |
| Same mix, examiner jobs reweighted to self-certified's mix | 36,834 | 7 | 85 | 22,236 | 80 | 515 | **73** |
| Same mix, self-certified jobs reweighted to examiner's mix | 36,834 | 9 | 153 | 22,236 | 99 | 571 | **90** |

**In plain terms:**
- **Most of the gap survives.** For Alterations alone, the gap is 72 days, which is **75% of the original 96**. With the job-type mix equalized, the gap is 73 to 90 days, which is **76% to 94%** of the original. The range depends on which route's mix you use.
- **About a quarter of the gap, at most, comes from job mix.**
- **For big jobs, the gap is wider in absolute days:** 128.5 days for Alteration CO and 218 for New Buildings.

**What this check does not rule out:**
- **The route isn't proven to *cause* the gap.** Even within one job type, the jobs on each route may differ in size, cost, complexity, building type or special approvals. Our download doesn't include those columns.
- **Applicants choose their route, and some jobs may not be eligible to self-certify.** Either way, harder jobs could cluster in examiner review.
- **Self-certified jobs aren't free of DOB scrutiny.** DOB says it *"audited nearly 25 percent of professionally certified applications post-approval"* in FY2026 ([MMR FY2026, p. 358](https://www.nyc.gov/assets/operations/downloads/pdf/mmr2026/dob.pdf)). Any audit time after approval isn't counted in our filing-to-permit measure.

**The right wording for public use:** "Within the same job type, self-certified jobs reached a permit much faster than examiner-reviewed jobs: a median of 7 vs 79 days for Alterations." Don't say "self-certifying saves 72 days."

## 9. Source check

Each city figure above comes from one of these sources. Page numbers are the reports' printed page numbers.

| Source | URL | Pages used |
|---|---|---|
| Mayor's Management Report, FY2026, Department of Buildings | https://www.nyc.gov/assets/operations/downloads/pdf/mmr2026/dob.pdf | 357–358 |
| Mayor's Management Report, FY2025, Department of Buildings | https://www.nyc.gov/assets/operations/downloads/pdf/mmr2025/dob.pdf | 357–358 |
| Preliminary Mayor's Management Report, FY2026, Department of Buildings | https://www.nyc.gov/assets/operations/downloads/pdf/pmmr2026/dob.pdf | 321–322, 325 |
| NY State Comptroller press release, July 2, 2026 (web page, not a PDF) | https://www.osc.ny.gov/press/releases/2026/07/dinapoli-nyc-department-buildings-meets-critical-goals-lags-lower-priority-issues | n/a |

**The "three times" claim, word for word.** MMR FY2026, the sentence runs from the bottom of p. 357 to the top of p. 358:

> "The time taken for a filing to reach approval is largely driven by how long the applicant is holding the filing while making corrections necessary to achieve approval, and is not under Department control. This time with the applicant is typically three times as long as the time the filing is with the Department for review."

The FY2025 MMR (pp. 357–358) has nearly the same wording ("how long the applicant holds the filing").

**What that sentence does and doesn't support:**
- **The earlier short version was too loose.** I said "applicants hold filings about 3 times as long as DOB reviews them." The report actually says *typically three times*, and it refers to the time from filing to *approval* only. It isn't about the whole wait to a permit.
- **It's DOB describing its own process.** The report gives no data, method or job-type breakdown behind "three times", and no performance indicator measures applicant time. Quote it as the city's claim, not as a measured fact.
- **The FY2026 preliminary report puts it more cautiously** ([PMMR FY2026, p. 321](https://www.nyc.gov/assets/operations/downloads/pdf/pmmr2026/dob.pdf)). It says *"The days-to-approval measure includes both the time an application is with the Department and time with the applicant,"* and that *"Filing complexities and submission quality, as well as resource constraints, contributed to extended plan review times and instances of rejection or resubmission."* It gives no ratio, and it names DOB's own resource limits as one of the causes.

## How to reproduce

```
python -m uv sync
python -m uv run python -m greenlight_nyc_v2.fetch --end 2026-11-18
python -m uv run python -m greenlight_nyc_v2.analyze
```

`fetch.py` saves raw files to `data/raw/` (not committed) and checks row counts against the server. Because the city keeps updating the dataset, a later download may differ slightly.
