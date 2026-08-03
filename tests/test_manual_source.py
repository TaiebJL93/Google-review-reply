import pytest

from app.sources.manual_source import ManualSource, ManualSourceError


def test_parses_multiple_reviews():
    text = (
        "Jane Doe\n5\nLoved the espresso and the quick service!\n\n"
        "Sam Lee\n2\nWaited 30 minutes with no apology.\nDate: 2024-05-04\n"
    )
    reviews = ManualSource(text).fetch()

    assert len(reviews) == 2
    assert reviews[0].author_name == "Jane Doe"
    assert reviews[0].rating == 5
    assert reviews[0].review_date is None
    assert reviews[1].review_date.isoformat() == "2024-05-04"
    assert reviews[1].body == "Waited 30 minutes with no apology."


def test_multiline_body():
    text = "Jane Doe\n5\nLine one.\nLine two."
    reviews = ManualSource(text).fetch()
    assert reviews[0].body == "Line one.\nLine two."


def test_empty_text_raises():
    with pytest.raises(ManualSourceError):
        ManualSource("   ").fetch()


def test_too_few_lines_raises():
    with pytest.raises(ManualSourceError, match="rating"):
        ManualSource("Jane Doe\n5").fetch()


@pytest.mark.parametrize("rating", ["0", "6", "abc"])
def test_invalid_rating_raises(rating):
    text = f"Jane Doe\n{rating}\nGreat service!"
    with pytest.raises(ManualSourceError, match="rating"):
        ManualSource(text).fetch()


def test_invalid_date_raises():
    text = "Jane Doe\n5\nGreat service!\nDate: not-a-date"
    with pytest.raises(ManualSourceError, match="date"):
        ManualSource(text).fetch()
