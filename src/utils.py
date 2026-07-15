"""
utils.py
--------
Utility helpers for cleaning and formatting generated text, as described in
the report's "Output Cleaning" step:

    "The decoded output is trimmed using the --- delimiter to remove
    irrelevant trailing text. Any duplicated lines are also filtered for
    readability."
"""

import re
from src.config import settings


def truncate_at_delimiter(text: str, delimiter: str = None) -> str:
    """
    Cut off everything from the first occurrence of `delimiter` onward.

    This is how the "predefined stopping point" from the report is
    enforced: once the model starts producing the delimiter (or drifts
    into a new, unrelated "To:"/"Subject:" block, which GPT-Neo sometimes
    does when it starts hallucinating a second email) we stop keeping text.
    """
    delimiter = delimiter or settings.STOP_DELIMITER
    if delimiter and delimiter in text:
        text = text.split(delimiter)[0]

    # GPT-Neo occasionally continues past one email and starts drafting a
    # second "To:"/"Subject:" block. Cut those off too.
    match = re.search(r"\n(To:|Subject:)", text)
    if match:
        text = text[: match.start()]

    return text.rstrip()


def remove_duplicate_lines(text: str) -> str:
    """
    Remove consecutive and exact duplicate lines while preserving overall
    paragraph structure and blank lines used for spacing.
    """
    lines = text.split("\n")
    seen = set()
    cleaned_lines = []
    previous_line = None

    for line in lines:
        stripped = line.strip()

        # Always keep blank lines (they preserve paragraph breaks), but
        # never allow two blank lines in a row.
        if stripped == "":
            if previous_line == "":
                continue
            cleaned_lines.append(line)
            previous_line = ""
            continue

        normalized = stripped.lower()
        if normalized in seen:
            continue

        seen.add(normalized)
        cleaned_lines.append(line)
        previous_line = stripped

    return "\n".join(cleaned_lines).strip()


def collapse_whitespace(text: str) -> str:
    """Collapse runs of 3+ blank lines down to a single blank line."""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_generated_text(raw_text: str, delimiter: str = None) -> str:
    """
    Full output-cleaning pipeline applied to raw model output:
    1. Truncate at the stop delimiter / next email block.
    2. Remove duplicate lines.
    3. Collapse excess whitespace.
    """
    text = truncate_at_delimiter(raw_text, delimiter)
    text = remove_duplicate_lines(text)
    text = collapse_whitespace(text)
    return text


def word_count(text: str) -> int:
    """Return the number of words in a piece of text."""
    return len(text.split())


def to_downloadable_filename(recipient: str, event: str) -> str:
    """Build a filesystem-safe filename for a "download email" button."""
    base = f"{recipient}_{event}".strip() or "email"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", base).strip("_").lower()
    return f"{safe or 'generated_email'}.txt"
