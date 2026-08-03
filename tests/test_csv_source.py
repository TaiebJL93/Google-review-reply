import pytest

from app.sources.csv_source import CsvSource, CsvSourceError


def test_parses_valid_rows():
    content = (
        "author_name,rating,body,review_date\n"
        "Jane Doe,5,Loved the coffee,2024-05-02\n"
        "Sam Lee,2,Waited too long,\n"
    )
    reviews = CsvSource(content).fetch()

    assert len(reviews) == 2
    assert reviews[0].author_name == "Jane Doe"
    assert reviews[0].rating == 5
    assert reviews[0].body == "Loved the coffee"
    assert reviews[0].review_date.isoformat() == "2024-05-02"
    assert reviews[1].review_date is None


def test_accepts_bytes_input():
    content = b"author_name,rating,body\nJane Doe,5,Great!\n"
    reviews = CsvSource(content).fetch()
    assert reviews[0].author_name == "Jane Doe"


def test_missing_required_column_raises():
    content = "author_name,rating\nJane Doe,5\n"
    with pytest.raises(CsvSourceError, match="body"):
        CsvSource(content).fetch()


def test_empty_csv_raises():
    with pytest.raises(CsvSourceError):
        CsvSource("").fetch()


def test_no_data_rows_raises():
    with pytest.raises(CsvSourceError, match="no data rows"):
        CsvSource("author_name,rating,body\n").fetch()


@pytest.mark.parametrize("rating", ["0", "6", "abc"])
def test_invalid_rating_raises(rating):
    content = f"author_name,rating,body\nJane Doe,{rating},Great!\n"
    with pytest.raises(CsvSourceError, match="rating"):
        CsvSource(content).fetch()


def test_blank_author_raises():
    content = "author_name,rating,body\n,5,Great!\n"
    with pytest.raises(CsvSourceError, match="author_name"):
        CsvSource(content).fetch()


def test_invalid_date_raises():
    content = "author_name,rating,body,review_date\nJane Doe,5,Great!,05/02/2024\n"
    with pytest.raises(CsvSourceError, match="review_date"):
        CsvSource(content).fetch()
