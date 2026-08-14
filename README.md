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

Edit `.env` and set `GEMINI_API_KEY` to a free key from
https://aistudio.google.com/apikey.

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

## Connecting a Google Business Profile account (planned, not yet built)

Today, reviews only come in via CSV upload or manual paste
(`app/sources/csv_source.py`, `app/sources/manual_source.py`). A
`GoogleBusinessSource` adapter already exists as an extension point
(`app/sources/google_source.py`) but its `fetch()` currently just raises
`NotImplementedError` — see "Out of scope for MVP" in
[docs/PLAN.md](docs/PLAN.md). This section documents the full path to
wiring it up for real, so a business owner (e.g. a coffee shop or
restaurant) could eventually connect their Google account and have reviews
sync in automatically instead of pasting them by hand.

### 1. Prerequisites (Google's side, before writing any code)

- The business must have a **Google Business Profile that is claimed and
  verified**, and Google generally expects it to have been active for a
  while (60+ days) before approving API access — a brand-new listing is
  likely to be rejected.
- A **Google Cloud project** to hold the OAuth credentials.
- The Business Profile APIs are **not self-serve**. You must submit
  [Google's API access request form](https://developers.google.com/my-business/content/prereqs)
  and describe the use case (owner managing replies to their own
  location's reviews). Approval is manual and typically takes several
  business days, not instant — build this lead time into any rollout plan.

### 2. Once access is approved

In the Google Cloud Console, enable the APIs Google's setup flow requires
(reviews live under the `mybusiness.googleapis.com` v4 API, but Google's
own basic-setup instructions have you enable the full family together):

- Google My Business API (this is the one with `accounts.locations.reviews.list`)
- My Business Account Management API
- My Business Business Information API
- My Business Notifications API
- My Business Verifications API
- My Business Place Actions API
- My Business Q&A API
- My Business Lodging API

Then create an **OAuth 2.0 Client ID** (Credentials → Create credentials →
OAuth client ID → Web application), with a redirect URI pointing at
whatever callback route this app adds (e.g.
`http://127.0.0.1:8000/auth/google/callback` for local dev). The token
request must include this scope:

```
https://www.googleapis.com/auth/business.manage
```

Add the resulting client ID/secret to `.env`, following the existing
`GEMINI_API_KEY` pattern in `app/config.py`:

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 3. What still needs to be built in this repo

None of this exists yet — it's the implementation work behind the
`GoogleBusinessSource` stub:

- OAuth authorize + callback routes (`/auth/google/...`) that run the
  consent flow and receive the authorization code.
- Persisting the resulting access/refresh token per `Business` (a new
  table or columns — nothing in `app/models.py` stores credentials today).
- Implementing `GoogleBusinessSource.fetch()` to call
  `accounts.locations.reviews.list`, paginated, for the connected location.
- Incremental sync: track the newest review's `updateTime` per business and
  only pull reviews newer than that on later syncs, instead of re-fetching
  full history every time (the stub's docstring in `google_source.py`
  outlines this).
- Mapping the API's `Review` resource (`reviewer.displayName`,
  `starRating`, `comment`, `createTime`) onto this app's `ReviewData`.
- A refresh-token renewal path, since access tokens expire and the sync
  needs to run unattended.

There is no billing for the Business Profile APIs themselves — access
approval is the real gate, not cost.

## Tests

See [TESTING.md](TESTING.md).
