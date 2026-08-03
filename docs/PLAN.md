# ReviewReply — Build Plan

## Problem

Local business owners get Google reviews faster than they can reply to them well.
Generic auto-reply templates ("Thank you for your feedback!") are easy for customers
to spot and make the business look disengaged — especially damaging on 1–2 star
reviews where a canned response reads as indifference. Writing a genuine, on-brand
reply to every review takes time most owners don't have.

ReviewReply drafts a response to a single review in ~10 seconds that:

- references at least one concrete detail from that specific review,
- sounds like the owner (not like a template), and
- handles negative reviews with an apology, a concrete remedy, and an invitation
  to follow up directly — without inventing facts about the visit.

The owner reviews, edits if needed, and copies the draft into Google — this tool
never posts on the owner's behalf.

## MVP Scope

In scope:
- Business profile (one owner, one business, for MVP).
- Voice profile via questionnaire + optional few-shot examples (past responses
  the owner actually wrote).
- Review import via CSV upload or manual paste.
- Dashboard listing reviews with a "Draft response" action per review.
- Draft generation via the Anthropic Messages API, editable before copying.
- Pluggable review-source adapters so a live Google Business Profile connector
  can be dropped in later without touching the rest of the app.

Out of scope for MVP (explicitly):
- Direct Google Business Profile API integration (reviews arrive via CSV/paste only).
- Posting replies back to Google automatically.
- Multi-user auth, billing, multi-business accounts.
- Any UI framework beyond Jinja2 templates + vanilla JS/htmx-style progressive
  enhancement.

## Build Order

1. **Docs first** — this file and `ARCHITECTURE.md`, so implementation has a fixed
   target instead of drifting.
2. **Data layer** — SQLAlchemy models for `Business`, `VoiceProfile`, `Review`,
   `Draft`; SQLite via a local file, created on startup.
3. **Review adapters** — `ReviewSource` ABC, `CsvSource`, `ManualSource`,
   `GoogleBusinessSource` stub.
4. **Generation service** — prompt builder (pure function, unit-testable without
   the network) + a thin Anthropic client wrapper.
5. **Routes + templates** — FastAPI routes for the setup flow, review import,
   dashboard, and draft generation; Jinja2 templates rendering server-side with a
   small amount of vanilla JS for the "Draft response" interaction (fetch +
   in-place DOM update, no build step).
6. **Tests** — CSV parsing, voice-profile validation, prompt construction
   (assert review specifics and voice attributes appear in the built prompt),
   and route tests with the Anthropic call mocked.
7. **README + TESTING docs**, `.env.example`, `.gitignore`.
8. **Git history** — one commit per meaningful step, not a single squash commit.

## Roadmap Beyond MVP

- **Google Business Profile integration**: implement `GoogleBusinessSource`
  (OAuth flow, review pull via the Business Profile API, incremental sync by
  review ID/timestamp). The adapter boundary already exists — this is additive,
  not a rewrite.
- **Posting replies back to Google**: once source integration exists, add a
  "Post to Google" action next to "Copy," gated behind an explicit owner
  confirmation per reply.
- **Multi-business / multi-user accounts**: introduce an `Owner` table above
  `Business`, add auth. Deferred because MVP targets a single owner testing the
  core value prop first.
- **Reply history feedback loop**: feed the owner's edits back into the voice
  profile's few-shot examples so generation improves over time.
- **Bulk drafting**: generate drafts for all unreplied reviews in one action,
  with a review queue instead of one-at-a-time.
