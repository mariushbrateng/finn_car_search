# FINN Car Search

This repo lets you scrape Finn.no for electric cars (currently Tesla Model 3/Model Y and Hyundai Ioniq 5), parse the listings into a tidy dataset, and explore prices in a Streamlit dashboard.

## Prerequisites

- Python 3.11
- [Poetry](https://python-poetry.org/) (2.2+)
- Finn.no account is **not** required because the scraper fetches publicly visible data, but be mindful of their terms of use and rate-limit your requests.

## Initial setup

```bash
git clone https://github.com/<you>/finn_car_search.git
cd finn_car_search
# Install dependencies
poetry install
# Create folder for raw HTML dumps
mkdir -p data/ads
```

## Configuration

`src/config.toml` drives what the crawler fetches:

```toml
[car_codes]
model_3 = "1.8078.2000501"
model_y = "1.8078.2000555"
ioniq_5 = "1.772.2000546"

[scraper]
basic_finn_url = "https://www.finn.no/mobility/search/car?registration_class=1&wheel_drive=2&model="

[filters]
year_from = 2022
year_to = 2022
```

Each `car_code` is Finn’s internal model identifier. The `wheel_drive=2` parameter limits searches to AWD/4x4 vehicles; tweak or extend the query string to add other filters Finn exposes. Optional `[filters]` constrain the crawl further (e.g., `year_from`/`year_to`). Remove or comment them out if you want all model years. To add/remove models:

1. Visit the Finn search UI, open the dev tools → Network tab, and copy the `model=` param from the URL when you filter by a specific model.
2. Update the `[car_codes]` section accordingly.
3. Commit & rerun the crawler.

## End-to-end workflow

1. **Crawler** – download raw listings as HTML:
   ```bash
   poetry run python src/crawler.py
   ```
   - Pagination is automatic.
   - The script skips ads you already downloaded (based on finnkode filenames stored under `data/ads/`).
2. **Scraper** – parse HTML into structured rows and write `data/ads.parquet`:
   ```bash
   poetry run python src/scraper.py
   ```
   - Uses Finn’s embedded JSON payload to extract title, brand, model, mileage, price, drivetrain, leasing flag, safety badges, etc.
   - Falls back to classic HTML parsing if Finn changes their payload.
3. **Dashboard** – explore the dataset locally:
   ```bash
   poetry run streamlit run src/app.py
   ```
   - The app auto-loads `data/ads.parquet`.
   - You can optionally pass `--server.port` or `--server.headless` flags.

## Deployment

### Streamlit Community Cloud (recommended)

1. Push this repository (including `data/ads.parquet` or logic to download it) to GitHub.
2. Generate `requirements.txt` whenever dependencies change:
   ```bash
   poetry export -f requirements.txt --output requirements.txt --without-hashes
   ```
3. On https://share.streamlit.io, point the app to `src/app.py`. Redeploy happens automatically on every push.

### Other options

- **Render**: create `render.yaml` for a web service running `streamlit run src/app.py`.
- **Docker/Fly.io**: bake a container and deploy anywhere you like.

## Keeping data fresh

- **Manual refresh**: rerun crawler + scraper locally, commit the updated `data/ads.parquet`, and push.
- **Automated**:
  - Upload the parquet file to S3/GCS/Azure Blob.
  - Store credentials/URL in environment variables or `.streamlit/secrets.toml`.
  - Schedule a GitHub Action (or cron job) to run `crawler.py` and `scraper.py`, upload the result, and trigger a redeploy.

## Troubleshooting

- **No ads collected**: Finn sometimes changes their public API. Check `src/crawler.py` for the latest JSON endpoint and update `basic_finn_url` + headers if necessary.
- **Streamlit sliders throw `NaN` errors**: ensure `data/ads.parquet` exists and includes required columns; the latest app build already guards against empty series.
- **Missing dependencies during deployment**: rerun `poetry export ...` so hosting providers consume the updated `requirements.txt`.

## Warning

Scraping FINN might violate their terms. Use at your own risk, respect robots.txt, and throttle requests (the current crawler respects pagination but you may want to insert sleeps/jitter for long runs).