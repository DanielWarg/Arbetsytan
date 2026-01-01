"""Leak check - Blocking preflight to detect remaining PII after masking."""
from typing import Dict
from .regex_mask import regex_masker
from .models import PrivacyLeakError


def check_leaks(text: str, mode: str = "balanced") -> None:
    """
    Check for remaining PII leaks in masked text (blocking).
    
    This is a FAIL-CLOSED check: ANY detected PII pattern = BLOCK.
    
    Args:
        text: Masked text to check
        mode: "strict" or "balanced" (both modes are strict for leak detection)
        
    Raises:
        PrivacyLeakError: If leaks detected
    """
    leaks = regex_masker.count_leaks(text)
    
    # Count total leaks - ANY leak is a failure (fail-closed)
    total_leaks = sum(leaks.values())
    
    if total_leaks > 0:
        # Log leak details (but don't expose in response)
        leak_details = {k: v for k, v in leaks.items() if v > 0}
        raise PrivacyLeakError(
            f"Privacy leak detected: {total_leaks} potential PII entities remaining",
            error_code="pii_detected"
        )

