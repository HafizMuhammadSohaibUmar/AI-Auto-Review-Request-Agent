"""Review tracking abstraction.

The Google Business Profile API is not required for the core demo. This class
keeps the integration boundary explicit so real GBP polling can be added later
without changing the follow-up handler.
"""


class ReviewTracker:
    async def has_review_for_job(self, customer_phone: str, job_id: str) -> bool:
        return False


review_tracker = ReviewTracker()
