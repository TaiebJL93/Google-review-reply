# ReviewReply — Architecture

## Components

```
app/
  main.py          FastAPI app, mounts routers, creates tables on startup
  config.py        Settings (env vars: ANTHROPIC_API_KEY, DATABASE_URL)
  database.py      SQLAlchemy engine/session setup
  models.py        ORM models: Business, VoiceProfile, Review, Draft
  schemas.py       Pydantic request/response models for form validation
  generation.py    Prompt builder + Anthropic client wrapper
  routes/
    business.py    Business + voice profile setup routes
    reviews.py     Review import (CSV/paste) + dashboard routes
    drafts.py      Draft generation + edit routes
  sources/
    base.py        ReviewSource abstract base class
    csv_source.py  CsvSource — parses uploaded/local CSV files
    manual_source.py  ManualSource — parses pasted free-text reviews
    google_source.py  GoogleBusinessSource — stub, NotImplementedError
  templates/       Jinja2 templates (dashboard, setup forms, draft partial)
  static/          Minimal CSS + vanilla JS for the draft-response interaction
seed_data/
  sample_reviews.csv   10 sample reviews for local testing
tests/
  test_csv_source.py
  test_voice_profile.py
  test_generation_prompt.py
  test_routes.py
```

## Data Model

```
Business
  id            int, PK
  name          str
  business_type str            e.g. "coffee shop", "auto repair"
  owner_name    str
  created_at    datetime

VoiceProfile (1:1 with Business)
  id                 int, PK
  business_id        int, FK -> Business.id
  tone               str        "warm" | "professional" | "casual"
  sign_off           str        e.g. "Warm regards, Maria"
  phrases_to_use     str        free text, comma-separated phrases
  phrases_to_avoid   str        free text, comma-separated phrases
  example_responses  str        newline-delimited past responses (0-5),
                                 used as few-shot examples

Review
  id             int, PK
  business_id    int, FK -> Business.id
  source         str        "csv" | "manual" | "google" (adapter that created it)
  author_name    str
  rating         int        1-5
  body           str
  review_date    date | null
  created_at     datetime

Draft (0/1 per Review; regenerating replaces the row)
  id           int, PK
  review_id    int, FK -> Review.id, unique
  content      str
  created_at   datetime
```

Rationale: `VoiceProfile` is 1:1 with `Business` rather than embedded on
`Business` directly so the setup-questionnaire step is a clearly separable
concern (and because the MVP flow treats "create business" and "set up voice"
as two distinct screens). `Draft` is a separate table (not a `Review.draft`
text column) so regeneration history could later become 1:many without a
migration that changes column semantics — for the MVP itself we keep it 1:1
and simply overwrite.

## Request Flow

1. **Setup**: `POST /business` creates a `Business`; `POST /business/{id}/voice`
   creates/updates its `VoiceProfile` from the questionnaire form (tone,
   sign-off, phrases, optional pasted example responses).
2. **Import**: `POST /reviews/import/csv` (file upload) or
   `POST /reviews/import/manual` (pasted text) hands the raw input to the
   matching `ReviewSource` adapter, which yields normalized `Review` objects
   that the route persists. The route layer never parses review text itself —
   that responsibility lives entirely in `sources/`.
3. **Dashboard**: `GET /dashboard` lists a business's reviews (newest first),
   each with a "Draft response" button and, if a `Draft` already exists, the
   current draft text inline.
4. **Draft generation**: `POST /reviews/{id}/draft` loads the `Review` and its
   business's `VoiceProfile`, calls `generation.build_prompt(review,
   voice_profile, recent_openings)` to construct the Anthropic messages
   payload, sends it via `generation.generate_reply(...)`, and upserts the
   result into `Draft`. The route returns an HTML partial (for htmx-style
   in-place swap) containing the editable draft.
5. **Approve/copy**: handled entirely client-side (an editable `<textarea>` +
   "Copy" button) — there is no "approved" state to persist because the MVP
   never posts back to Google.

## Prompt Design Rationale

The prompt builder (`generation.build_prompt`) is a pure function — no network
call — so it can be unit-tested by asserting on the string/messages it
produces. It is built from four inputs:

- **The review**: author, rating, body, date if known.
- **The voice profile**: tone, sign-off, phrases to use/avoid, owner name,
  business type.
- **Few-shot examples**: if the owner pasted past responses, up to 5 are
  included verbatim as examples of their actual voice — this is weighted more
  heavily than the questionnaire fields, since real writing samples are a
  stronger signal than self-reported tone.
- **Recent opening lines**: the first few words of the last N generated
  drafts for that business, passed in explicitly and the model instructed not
  to reuse them — this is what prevents consecutive replies from reading as
  templated, since an LLM given the same instructions twice will otherwise
  gravitate to the same opening.

Hard constraints enforced via explicit system-prompt instructions (not
post-processing, since post-processing can't fix a fabricated fact but a
system-prompt boundary can prevent one from being generated):

- Reference at least one concrete detail from the review body.
- Match the voice profile's tone and use its sign-off.
- 1–2 star reviews: apology + a concrete remedy + invitation to contact
  directly (phone/email is not fabricated — the instruction is to invite
  contact, not to invent contact details).
- Never invent facts about the customer's visit beyond what the review states.
- 2–5 sentences.

`generation.generate_reply` wraps the Anthropic Messages API call
(`model="claude-sonnet-5"`) behind a single function so route tests can mock
it entirely — no test in this repo makes a live network call.

## Review Source Adapters

`sources.base.ReviewSource` defines one method, `fetch() -> list[ReviewData]`,
where `ReviewData` is a plain dataclass (author, rating, body, review_date).
This keeps the interface small enough that a future `GoogleBusinessSource`
only needs to implement `fetch()` against the real API — everything upstream
(persistence, dashboard, generation) is adapter-agnostic. `GoogleBusinessSource`
currently raises `NotImplementedError` with a docstring describing the OAuth +
Business Profile API flow it will need.
