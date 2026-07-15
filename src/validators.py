"""
validators.py
--------------
Input validation helpers for the email generator.

Keeping validation logic separate from the UI and generation code makes it
reusable (e.g. testable in isolation, or reused by a future REST API) and
keeps `app.py` focused on presentation.
"""

import re
from dataclasses import dataclass, field
from typing import List


# Basic guard-rails against nonsensical or unsafe inputs. These are
# intentionally permissive (this is a text tool, not a strict form) --
# they exist to catch empty/garbage input, not to police phrasing.
_MAX_FIELD_LENGTH = 500
_MIN_NAME_LENGTH = 2
_SUSPICIOUS_CHARS = re.compile(r"[<>{}$`]")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.is_valid = False
        self.errors.append(message)


def validate_email_request(
    recipient: str,
    event: str,
    extra_info: str = "",
    sender_name: str = "",
) -> ValidationResult:
    """
    Validate the raw inputs collected from the UI before they are turned
    into a prompt.

    Returns a ValidationResult with `is_valid` and a list of human-readable
    error messages suitable for direct display in the UI.
    """
    result = ValidationResult(is_valid=True)

    if not recipient or not recipient.strip():
        result.add_error("Recipient name is required.")
    elif len(recipient.strip()) < _MIN_NAME_LENGTH:
        result.add_error("Recipient name looks too short. Please double-check it.")
    elif len(recipient) > _MAX_FIELD_LENGTH:
        result.add_error(f"Recipient name must be under {_MAX_FIELD_LENGTH} characters.")
    elif _SUSPICIOUS_CHARS.search(recipient):
        result.add_error("Recipient name contains unsupported characters.")

    if not event or not event.strip():
        result.add_error("Event / subject description is required.")
    elif len(event) > _MAX_FIELD_LENGTH:
        result.add_error(f"Event description must be under {_MAX_FIELD_LENGTH} characters.")
    elif _SUSPICIOUS_CHARS.search(event):
        result.add_error("Event description contains unsupported characters.")

    if extra_info and len(extra_info) > _MAX_FIELD_LENGTH * 2:
        result.add_error(
            f"Additional instructions must be under {_MAX_FIELD_LENGTH * 2} characters."
        )
    if extra_info and _SUSPICIOUS_CHARS.search(extra_info):
        result.add_error("Additional instructions contain unsupported characters.")

    if sender_name and len(sender_name) > _MAX_FIELD_LENGTH:
        result.add_error(f"Sender name must be under {_MAX_FIELD_LENGTH} characters.")

    return result
