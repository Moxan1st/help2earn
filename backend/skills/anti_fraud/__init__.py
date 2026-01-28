"""Anti-Fraud Skill - Duplicate and fraud detection."""
from .skill import (
    check_fraud,
    check_user_submission_rate,
    check_location_validity,
    get_fraud_statistics
)

__all__ = [
    "check_fraud",
    "check_user_submission_rate",
    "check_location_validity",
    "get_fraud_statistics"
]
