from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date as date_type
from typing import List, Optional


@dataclass
class ReviewData:
    author_name: str
    rating: int
    body: str
    review_date: Optional[date_type] = None
    external_id: Optional[str] = None


class ReviewSource(ABC):
    """Normalizes raw review input from a particular channel into ReviewData."""

    @abstractmethod
    def fetch(self) -> List[ReviewData]:
        ...
