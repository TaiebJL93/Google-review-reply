# Testing

```bash
pip install -r requirements.txt
pytest
```

No test in this suite makes a live network call — `tests/test_routes.py`
mocks `app.routes.drafts.generate_reply` via `monkeypatch` instead of calling
the Anthropic API, and every test runs against an in-memory SQLite database
(`tests/conftest.py`), reset between tests by an autouse fixture.

`pytest.ini` sets `pythonpath = .` so `import app...` resolves regardless of
the working directory `pytest` is invoked from.

## Coverage

- `tests/test_csv_source.py`, `tests/test_manual_source.py` — parsing and
  validation edge cases for the two review-import adapters (missing
  columns/lines, out-of-range ratings, malformed dates, blank fields).
- `tests/test_voice_profile.py` — `VoiceProfileForm` validation (tone enum,
  blank sign-off, the 5-example-response limit).
- `tests/test_generation_prompt.py` — asserts `generation.build_prompt` is a
  pure function whose output contains the review's specifics (author,
  rating, body, date) and the voice profile's attributes (tone, sign-off,
  phrases, business type/owner, few-shot examples), plus the recent-openings
  avoidance instruction.
- `tests/test_routes.py` — the full request flow (create business → set
  voice profile → import via CSV/manual paste → generate a draft → draft
  persists across a dashboard reload), plus the 400/404 error paths.
