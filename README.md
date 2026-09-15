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

Visit http://127.0.0.1:8000/ — you'll land on `/signup` first. Create an
account with an email and password, which signs you in and redirects to
`/setup` to create your business and voice profile, then to the dashboard.
Each account only sees the businesses it created (see "Accounts" below).
Import reviews from the dashboard's "Import reviews" link, either by
uploading a CSV (see `seed_data/sample_reviews.csv` for the expected
columns) or by pasting review text directly.

The SQLite database file (`reviewreply.db`) is created automatically on
startup in the project root.

![ReviewReply dashboard](docs/screenshots/dashboard.png)

## Accounts

Signing up (`/signup`) creates a `User` row and logs you in; `/login` and
`/logout` handle returning sessions. Passwords are hashed with
PBKDF2-HMAC-SHA256 (`app/auth.py`) — never stored or logged in plain text.
Every `Business` belongs to exactly one `User`, and all business/review/draft
routes 404 (not 403) on another account's data, so business IDs can't be
probed to confirm they exist. Visiting any page without an active session
redirects to `/login?next=<original path>`, which sends you back there after
a successful login.

If you're upgrading a database that predates accounts (rows in `businesses`
with no owner), the first person to sign up on that database automatically
adopts all ownerless businesses — no manual migration needed.

## Connecting a Google Business Profile account

Reviews can come in three ways: CSV upload, manual paste, or now a live
Google Business Profile connection (`app/sources/google_source.py`,
`app/routes/google_auth.py`). The OAuth flow, token storage, and sync are
fully implemented — what's missing is Google's approval of API access,
which is external to this app and can't be skipped (see prerequisites
below). Until that's approved, use CSV/paste as usual.

### Using it once you have credentials

1. Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`
   to `.env` (see `.env.example` — `GOOGLE_REDIRECT_URI` defaults to
   `http://127.0.0.1:8000/auth/google/callback` for local dev and must
   exactly match the redirect URI registered on the OAuth client).
2. On the dashboard, click **Connect Google** and complete the consent
   screen. This auto-selects the first Business Profile location returned
   for the account — a business with multiple locations isn't supported
   yet (no location picker).
3. Click **Sync Google reviews** any time to pull in new reviews since the
   last sync. Reviews already imported are skipped (deduped by Google's
   review ID), so it's safe to click repeatedly.
4. **Disconnect** removes the stored tokens and stops the sync option from
   showing; it doesn't delete reviews already imported.

Tokens are stored per business in the `google_connections` table
(`app/models.py`); access tokens are refreshed automatically when expired.

### 1. Prerequisites (Google's side — this is the real gate, not the code)

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
OAuth client ID → Web application), with the redirect URI set to this
app's callback route — `http://127.0.0.1:8000/auth/google/callback` for
local dev, or your deployed host's equivalent. The token request must
include this scope:

```
https://www.googleapis.com/auth/business.manage
```

Add the resulting client ID/secret to `.env` — see `.env.example`.

### 3. Known limitations of the current implementation

- **Single location only**: the callback auto-connects the first Business
  Profile location returned for the account. Multi-location businesses
  would need a location-picker step added to `app/routes/google_auth.py`.
- **No CSRF nonce on the OAuth `state` param**: `state` just carries the
  business ID through the redirect round-trip. Acceptable for this MVP's
  single-owner, no-login model, but would need a signed/session-bound
  state value if multi-user auth is ever added.
- **No reply-posting back to Google**: this only pulls reviews in; replies
  are still copy-pasted by the owner (see "Out of scope for MVP" in
  [docs/PLAN.md](docs/PLAN.md)).
- **Manual sync only**: there's no scheduled/background sync — the owner
  clicks "Sync Google reviews" on the dashboard when they want fresh data.

There is no billing for the Business Profile APIs themselves — access
approval is the real gate, not cost.

## Tests

See [TESTING.md](TESTING.md).

## Deploying for free (Render + Neon + a free domain)

This gives you a public URL like `https://your-app.onrender.com`, plus
optionally a custom domain like `yourapp.dpdns.org`. Three free accounts
are involved — this repo is already configured for all three (`render.yaml`,
`app/config.py`'s `postgres://` → `postgresql://` normalization, the
`SECRET_KEY`/`RENDER` env handling), but account creation, dashboard clicks,
and email verification have to happen on your end — no tool here can do
that for you.

### 1. Database — [Neon](https://neon.tech) (free Postgres, no expiry)

Render's own free tier has no persistent disk, so the SQLite file this app
uses locally would be wiped on every redeploy or idle spin-down — production
needs a database that lives outside Render. Neon's free tier doesn't expire
(unlike Render's own free Postgres, which is deleted 30 days after
creation).

1. Sign up at neon.tech, create a project.
2. Copy the connection string it gives you (starts with `postgresql://` or
   `postgres://` — both work, see the normalization note above). You'll
   paste this into Render as `DATABASE_URL` in the next step.

### 2. Hosting — [Render](https://render.com)

1. Sign up at render.com and connect your GitHub account.
2. New → Blueprint → select this repo. Render will detect `render.yaml`
   (already in this repo) and set up the web service automatically,
   including a randomly generated `SECRET_KEY`.
3. When prompted for the remaining env vars `render.yaml` declares, fill in:
   - `DATABASE_URL` — the Neon connection string from step 1.
   - `GEMINI_API_KEY` — from https://aistudio.google.com/apikey.
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — only if you've set up the
     Google Business Profile connection (see above); leave blank otherwise.
   - `GOOGLE_REDIRECT_URI` — set to `https://<your-render-subdomain>.onrender.com/auth/google/callback`
     once Render assigns you a URL, and update the redirect URI on the
     Google OAuth client to match exactly.
4. Deploy. First load after any idle period takes about a minute (free
   tier spins down after 15 minutes of no traffic) — expected, not a bug.
5. Once live, the first thing to do on the deployed URL is sign up for an
   account (see "Accounts" above) — production starts with no users either.

### 3. Free domain — [DigitalPlat FreeDomain](https://dash.domain.digitalplat.org)

1. Sign up at dash.domain.digitalplat.org and register a subdomain under
   one of the offered suffixes (`.dpdns.org`, `.qzz.io`, `.us.kg`, `.xx.kg`,
   `.qd.je`).
2. In Render: your service → Settings → Custom Domains → add the domain
   you registered. Render shows you a CNAME target.
3. Back in the DigitalPlat dashboard, add a CNAME record pointing your
   subdomain at the target Render gave you. DNS propagation can take a
   few minutes to a few hours.
4. If you set up Google OAuth, update `GOOGLE_REDIRECT_URI` (both in
   Render's env vars and on the Google OAuth client) to use the new
   custom domain instead of the `onrender.com` one.
