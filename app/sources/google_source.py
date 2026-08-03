from typing import List

from app.sources.base import ReviewData, ReviewSource


class GoogleBusinessSource(ReviewSource):
    """
    Stub for the future Google Business Profile integration.

    Real implementation will need:
      1. An OAuth 2.0 flow authorizing against the business's Google Business
         Profile account (offline access token, refreshed as needed).
      2. Calls to the Business Profile API's reviews.list endpoint, paginated,
         scoped to the connected location.
      3. Incremental sync: track the newest review's update time (or review
         name/ID) per business and only fetch reviews newer than that on
         subsequent syncs, instead of re-pulling the full history each time.
      4. Mapping the API's Review resource (reviewer displayName, starRating,
         comment, createTime) onto ReviewData.

    Not implemented for the MVP: reviews arrive via CsvSource or ManualSource
    only (see docs/PLAN.md, "Out of scope for MVP").
    """

    def __init__(self, *args, **kwargs):
        pass

    def fetch(self) -> List[ReviewData]:
        raise NotImplementedError(
            "GoogleBusinessSource is not implemented yet. Import reviews via "
            "CSV upload or manual paste for now."
        )
