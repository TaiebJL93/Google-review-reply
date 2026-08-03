import csv
import io
from datetime import datetime
from typing import List, Union

from app.sources.base import ReviewData, ReviewSource

REQUIRED_COLUMNS = {"author_name", "rating", "body"}


class CsvSourceError(ValueError):
    pass


class CsvSource(ReviewSource):
    """Parses a CSV with columns: author_name, rating, body, review_date (optional, YYYY-MM-DD)."""

    def __init__(self, content: Union[str, bytes]):
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        self._content = content

    def fetch(self) -> List[ReviewData]:
        reader = csv.DictReader(io.StringIO(self._content))
        if reader.fieldnames is None:
            raise CsvSourceError("CSV file is empty.")

        columns = {c.strip() for c in reader.fieldnames}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise CsvSourceError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")

        reviews = [self._parse_row(row, line_no) for line_no, row in enumerate(reader, start=2)]
        if not reviews:
            raise CsvSourceError("CSV has no data rows.")
        return reviews

    def _parse_row(self, row: dict, line_no: int) -> ReviewData:
        author = (row.get("author_name") or "").strip()
        if not author:
            raise CsvSourceError(f"Row {line_no}: author_name is required.")

        rating_raw = (row.get("rating") or "").strip()
        try:
            rating = int(rating_raw)
        except ValueError:
            raise CsvSourceError(f"Row {line_no}: rating must be an integer, got {rating_raw!r}.")
        if not 1 <= rating <= 5:
            raise CsvSourceError(f"Row {line_no}: rating must be between 1 and 5, got {rating}.")

        body = (row.get("body") or "").strip()
        if not body:
            raise CsvSourceError(f"Row {line_no}: body is required.")

        review_date = None
        date_raw = (row.get("review_date") or "").strip()
        if date_raw:
            try:
                review_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
            except ValueError:
                raise CsvSourceError(f"Row {line_no}: review_date must be YYYY-MM-DD, got {date_raw!r}.")

        return ReviewData(author_name=author, rating=rating, body=body, review_date=review_date)
