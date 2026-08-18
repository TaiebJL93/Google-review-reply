from datetime import datetime, timedelta
from typing import List, Optional

from app.google_client import list_reviews, refresh_access_token
from app.models import GoogleConnection
from app.sources.base import ReviewData, ReviewSource

_STAR_RATING_MAP = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
}

# Refresh a little before actual expiry to avoid a request failing mid-sync
# on a token that expires in the next few seconds.
_TOKEN_REFRESH_SKEW = timedelta(seconds=60)


class GoogleBusinessSource(ReviewSource):
    """Pulls reviews for one connected Business Profile location.

    See docs/PLAN.md, "Google Business Profile integration" for the roadmap
    context this implements.
    """

    def __init__(self, connection: GoogleConnection):
        self.connection = connection

    def fetch(self) -> List[ReviewData]:
        access_token = self._get_valid_access_token()
        cutoff = self.connection.last_synced_review_time

        results: List[ReviewData] = []
        page_token: Optional[str] = None
        while True:
            page = list_reviews(access_token, self.connection.location_name, page_token)
            for review in page.get("reviews", []):
                data = self._map_review(review)
                if data is None:
                    continue
                if cutoff and data.review_date and data.review_date <= cutoff.date():
                    continue
                results.append(data)

            page_token = page.get("nextPageToken")
            if not page_token:
                break

        return results

    def _get_valid_access_token(self) -> str:
        if self.connection.token_expires_at <= datetime.utcnow() + _TOKEN_REFRESH_SKEW:
            tokens = refresh_access_token(self.connection.refresh_token)
            self.connection.access_token = tokens.access_token
            self.connection.token_expires_at = datetime.utcnow() + timedelta(
                seconds=tokens.expires_in
            )
        return self.connection.access_token

    @staticmethod
    def _map_review(review: dict) -> Optional[ReviewData]:
        comment = review.get("comment", "")
        update_time_raw = review.get("updateTime") or review.get("createTime")
        review_date = None
        if update_time_raw:
            # Google returns RFC3339 UTC, e.g. "2026-08-01T14:23:00Z".
            review_date = datetime.fromisoformat(update_time_raw.replace("Z", "+00:00")).date()

        return ReviewData(
            author_name=review.get("reviewer", {}).get("displayName") or "Anonymous",
            rating=_STAR_RATING_MAP.get(review.get("starRating"), 0),
            body=comment,
            review_date=review_date,
            external_id=review.get("reviewId") or review.get("name"),
        )
