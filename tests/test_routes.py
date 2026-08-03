import io
import re


def _create_business(client):
    response = client.post(
        "/businesses",
        data={"name": "Java Hut", "business_type": "coffee shop", "owner_name": "Maria Ortiz"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].split("/")[2])


def _set_voice_profile(client, business_id):
    response = client.post(
        f"/businesses/{business_id}/voice",
        data={
            "tone": "warm",
            "sign_off": "Warm regards, Maria",
            "phrases_to_use": "thank you",
            "phrases_to_avoid": "",
            "example_responses": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _extract_first_review_id(html: str) -> str:
    match = re.search(r'data-draft-review-id="(\d+)"', html)
    assert match, "expected a draft button in the dashboard HTML"
    return match.group(1)


def test_create_business_redirects_to_voice_setup(client):
    response = client.post(
        "/businesses",
        data={"name": "Java Hut", "business_type": "coffee shop", "owner_name": "Maria Ortiz"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/voice-setup" in response.headers["location"]


def test_create_business_blank_name_returns_errors(client):
    response = client.post(
        "/businesses",
        data={"name": "  ", "business_type": "coffee shop", "owner_name": "Maria Ortiz"},
    )
    assert response.status_code == 422
    assert "required" in response.text.lower()


def test_voice_setup_and_dashboard(client):
    business_id = _create_business(client)
    _set_voice_profile(client, business_id)

    response = client.get(f"/businesses/{business_id}/dashboard")
    assert response.status_code == 200
    assert "Java Hut" in response.text


def test_csv_import_populates_dashboard(client):
    business_id = _create_business(client)
    _set_voice_profile(client, business_id)

    csv_content = "author_name,rating,body\nJane Doe,5,Loved the oat milk latte!\n"
    response = client.post(
        f"/businesses/{business_id}/import/csv",
        files={"file": ("reviews.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    assert "Jane Doe" in dashboard.text
    assert "Loved the oat milk latte" in dashboard.text


def test_manual_import_populates_dashboard(client):
    business_id = _create_business(client)
    _set_voice_profile(client, business_id)

    response = client.post(
        f"/businesses/{business_id}/import/manual",
        data={"text": "Sam Lee\n2\nWaited too long for a table."},
        follow_redirects=False,
    )
    assert response.status_code == 303

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    assert "Sam Lee" in dashboard.text


def test_draft_generation_is_mocked_and_persisted(client, monkeypatch):
    business_id = _create_business(client)
    _set_voice_profile(client, business_id)
    client.post(
        f"/businesses/{business_id}/import/manual",
        data={"text": "Jane Doe\n5\nLoved the espresso!"},
    )

    monkeypatch.setattr(
        "app.routes.drafts.generate_reply",
        lambda review, voice_profile, recent_openings=None: "Thanks so much, Jane! Warm regards, Maria",
    )

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    review_id = _extract_first_review_id(dashboard.text)

    response = client.post(f"/reviews/{review_id}/draft")
    assert response.status_code == 200
    assert "Thanks so much, Jane!" in response.text

    dashboard_after = client.get(f"/businesses/{business_id}/dashboard")
    assert "Thanks so much, Jane!" in dashboard_after.text


def test_draft_without_voice_profile_returns_400(client):
    business_id = _create_business(client)
    client.post(
        f"/businesses/{business_id}/import/manual",
        data={"text": "Jane Doe\n5\nLoved the espresso!"},
    )

    dashboard = client.get(f"/businesses/{business_id}/dashboard")
    review_id = _extract_first_review_id(dashboard.text)

    response = client.post(f"/reviews/{review_id}/draft")
    assert response.status_code == 400


def test_draft_for_unknown_review_returns_404(client):
    response = client.post("/reviews/9999/draft")
    assert response.status_code == 404
