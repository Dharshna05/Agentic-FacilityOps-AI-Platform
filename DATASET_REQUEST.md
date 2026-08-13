# Dataset Request — Energy Intelligence Module

Sending this so whoever has the Kaggle file (Power Consumption + Outdoor
Temperature + Occupancy) knows exactly what to hand over and why.

## What we need

The CSV file, as-is, exported from Kaggle. No cleaning/preprocessing needed
on your end — the backend will handle that. Just need the raw columns:

| Column (yours) | Meaning |
|---|---|
| `date` | Timestamp of each reading |
| `Power Consumption` | Total facility power draw (kW) |
| `Outdoor Temperature` | Outdoor temp (°C) |
| `Occupancy` | Headcount / occupancy level |

If it's literally `hammadkhan29/energy-consumption-temperature-occupancy-dataset`
on Kaggle, that's the one — 15-minute intervals, May–Dec 2018, ~21,500 rows.

## Why we need it (not strictly required, but better)

The backend currently ships with a working dataset already (35,040 rows,
built from 3 real public sources — PJM grid load, Environment Canada
weather, UCI occupancy sensors — stitched onto one timeline). It works and
is fully tested.

Your Kaggle file would be **better** because it's one real building,
recorded continuously, so Power/Temperature/Occupancy are *actually*
correlated with each other (AC responding to real heat, load responding to
real people walking in) — not three independent datasets stitched together.
More defensible for evaluation/demo if anyone asks "is this real data."

## How to send it

Just the raw `.xlsx` or `.csv` file, however you have it (Kaggle download,
Google Drive link, WhatsApp, whatever's easiest). No need to touch/clean it
first — column names, casing, and format (Excel or CSV) are auto-detected.

## What happens once we have it

Drop-in — no manual reformatting needed:
1. Open `http://localhost:8000/docs`
2. Find `POST /api/energy/ingest/upload`
3. Upload the file — that's it

The backend auto-detects your columns (`date` / `Power Consumption` /
`Outdoor Temperature` / `Occupancy` or close variants), maps them onto our
schema, derives the HVAC/Lighting/Plug/Other submeter split from your real
total using standard load-share ratios, and reloads the database.
Dashboard, analytics, and recommendations update automatically — nothing
else in the app changes.

Turnaround: instant, no code changes needed on our side.
