# ReviewReply

Drafts on-brand replies to Google reviews in seconds, so a business owner
always has a genuine starting point instead of a generic template. See
[docs/PLAN.md](docs/PLAN.md) for the problem this solves and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it's built.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env        # Windows; cp on macOS/Linux
```

Edit `.env` and set `ANTHROPIC_API_KEY` to a real key from
https://console.anthropic.com/.

## Run

```bash
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/ — on first run this redirects to `/setup` to
create your business and voice profile, then to the dashboard. Import
reviews from the dashboard's "Import reviews" link, either by uploading a
CSV (see `seed_data/sample_reviews.csv` for the expected columns) or by
pasting review text directly.

The SQLite database file (`reviewreply.db`) is created automatically on
startup in the project root.

## Tests

See [TESTING.md](TESTING.md).
