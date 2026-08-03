from datetime import datetime
from typing import List

from app.sources.base import ReviewData, ReviewSource


class ManualSourceError(ValueError):
    pass


class ManualSource(ReviewSource):
    """
    Parses pasted free-text reviews. Reviews are separated by a blank line;
    each review block is:

        Author Name
        Rating (1-5)
        Review body text, can span multiple lines
        Date: YYYY-MM-DD          (optional, must be the block's last line)
    """

    def __init__(self, text: str):
        self._text = text

    def fetch(self) -> List[ReviewData]:
        blocks = [b.strip() for b in self._text.strip().split("\n\n") if b.strip()]
        if not blocks:
            raise ManualSourceError("No reviews found in pasted text.")
        return [self._parse_block(block, i) for i, block in enumerate(blocks, start=1)]

    def _parse_block(self, block: str, index: int) -> ReviewData:
        lines = [line for line in block.splitlines() if line.strip() != ""]
        if len(lines) < 3:
            raise ManualSourceError(
                f"Review {index}: expected an author line, a rating line, and a body."
            )

        author = lines[0].strip()

        rating_raw = lines[1].strip()
        try:
            rating = int(rating_raw)
        except ValueError:
            raise ManualSourceError(f"Review {index}: rating must be an integer, got {rating_raw!r}.")
        if not 1 <= rating <= 5:
            raise ManualSourceError(f"Review {index}: rating must be between 1 and 5, got {rating}.")

        body_lines = lines[2:]
        review_date = None
        if body_lines and body_lines[-1].strip().lower().startswith("date:"):
            date_raw = body_lines[-1].split(":", 1)[1].strip()
            try:
                review_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
            except ValueError:
                raise ManualSourceError(f"Review {index}: date must be YYYY-MM-DD, got {date_raw!r}.")
            body_lines = body_lines[:-1]

        body = "\n".join(body_lines).strip()
        if not body:
            raise ManualSourceError(f"Review {index}: body is required.")

        return ReviewData(author_name=author, rating=rating, body=body, review_date=review_date)
