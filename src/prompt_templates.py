"""
prompt_templates.py
--------------------
All prompt-engineering logic lives here, isolated from generation and UI
code, as recommended in the original project report ("Prompt Engineering"
section).

Each template follows the structured format described in the report:

    To: [Recipient]
    Subject: <context-appropriate subject line>
    Dear [Recipient],
    I hope this message finds you well...
    <body driven by user-supplied context>
    ---

The trailing `---` delimiter is a stopping signal: generation is truncated
at the first occurrence of this delimiter to prevent the model from
producing irrelevant or repetitive trailing text (see report, section
"Challenges Faced and Solutions" -> Repetitive outputs).
"""

from enum import Enum
from src.config import settings


class EmailType(str, Enum):
    """All email categories supported by the generator."""

    PROFESSIONAL = "Professional"
    LEAVE_REQUEST = "Leave Request"
    JOB_APPLICATION = "Job Application"
    COMPLAINT = "Complaint"
    THANK_YOU = "Thank You"
    FOLLOW_UP = "Follow-up"
    INVITATION = "Invitation"
    FORMAL = "Formal"
    INFORMAL = "Informal"


# Human-readable descriptions shown in the UI's dropdown / help text.
EMAIL_TYPE_DESCRIPTIONS = {
    EmailType.PROFESSIONAL: "A general professional email for workplace communication.",
    EmailType.LEAVE_REQUEST: "A formal request for leave of absence to a manager or HR.",
    EmailType.JOB_APPLICATION: "A cover-letter style email applying for a position.",
    EmailType.COMPLAINT: "A formal complaint about a product, service, or issue.",
    EmailType.THANK_YOU: "A warm note of appreciation or gratitude.",
    EmailType.FOLLOW_UP: "A polite follow-up on a previous conversation or application.",
    EmailType.INVITATION: "An invitation to an event, meeting, or gathering.",
    EmailType.FORMAL: "A generic formal email suitable for official correspondence.",
    EmailType.INFORMAL: "A casual, friendly email between acquaintances or colleagues.",
}

# Per-type "intent" line injected into the prompt right after the greeting.
# This is the core piece of prompt engineering: it nudges GPT-Neo's
# continuation toward the right register and content for each email type.
_INTENT_LINES = {
    EmailType.PROFESSIONAL: (
        "I am writing to you regarding {event}. {extra_info}"
    ),
    EmailType.LEAVE_REQUEST: (
        "I am writing to formally request leave regarding {event}. {extra_info}"
    ),
    EmailType.JOB_APPLICATION: (
        "I am writing to express my interest in {event}. {extra_info}"
    ),
    EmailType.COMPLAINT: (
        "I am writing to raise a concern regarding {event}. {extra_info}"
    ),
    EmailType.THANK_YOU: (
        "I wanted to take a moment to thank you for {event}. {extra_info}"
    ),
    EmailType.FOLLOW_UP: (
        "I am following up regarding {event}. {extra_info}"
    ),
    EmailType.INVITATION: (
        "I am delighted to invite you to {event}. {extra_info}"
    ),
    EmailType.FORMAL: (
        "I am writing to you concerning {event}. {extra_info}"
    ),
    EmailType.INFORMAL: (
        "Just wanted to drop a quick note about {event}. {extra_info}"
    ),
}

# Per-type subject line prefix.
_SUBJECT_PREFIXES = {
    EmailType.PROFESSIONAL: "Regarding",
    EmailType.LEAVE_REQUEST: "Leave Request –",
    EmailType.JOB_APPLICATION: "Application for",
    EmailType.COMPLAINT: "Complaint Regarding",
    EmailType.THANK_YOU: "Thank You for",
    EmailType.FOLLOW_UP: "Follow-up on",
    EmailType.INVITATION: "Invitation to",
    EmailType.FORMAL: "Regarding",
    EmailType.INFORMAL: "About",
}

# Salutation style per type (formal types get "Dear", informal gets "Hi").
_SALUTATIONS = {
    EmailType.INFORMAL: "Hi {recipient},",
}
_DEFAULT_SALUTATION = "Dear {recipient},"

# Closing/sign-off per type.
_CLOSINGS = {
    EmailType.INFORMAL: "Thanks a lot,",
    EmailType.THANK_YOU: "With sincere gratitude,",
    EmailType.COMPLAINT: "Regards,",
    EmailType.JOB_APPLICATION: "Sincerely,",
    EmailType.LEAVE_REQUEST: "Sincerely,",
}
_DEFAULT_CLOSING = "Best regards,"


def build_prompt(
    email_type: EmailType,
    recipient: str,
    event: str,
    extra_info: str = "",
    sender_name: str = "",
) -> str:
    """
    Build a structured GPT-Neo prompt for the given email type and inputs.

    Parameters
    ----------
    email_type : EmailType
        The category of email to generate.
    recipient : str
        The name of the person the email is addressed to.
    event : str
        The subject / occasion / reason for the email.
    extra_info : str, optional
        Additional context or instructions supplied by the user.
    sender_name : str, optional
        The sender's name, appended after the closing line.

    Returns
    -------
    str
        A fully-formed prompt ready to be tokenized and passed to the model.
    """
    recipient = recipient.strip() or "Sir/Madam"
    event = event.strip()
    extra_info = extra_info.strip()

    subject_prefix = _SUBJECT_PREFIXES.get(email_type, "Regarding")
    salutation_template = _SALUTATIONS.get(email_type, _DEFAULT_SALUTATION)
    closing = _CLOSINGS.get(email_type, _DEFAULT_CLOSING)

    intent_line = _INTENT_LINES[email_type].format(
        event=event, extra_info=extra_info
    ).strip()

    salutation = salutation_template.format(recipient=recipient)

    lines = [
        f"To: {recipient}",
        f"Subject: {subject_prefix} {event}".strip(),
        "",
        salutation,
        "I hope this message finds you well.",
        intent_line,
    ]

    body_text = "\n".join(line for line in lines if line is not None)

    # NOTE: the prompt intentionally stops right after the "intent" line so
    # that GPT-Neo generates the actual email body, closing, and signature
    # as a continuation. The stop delimiter is NOT injected into the prompt
    # itself -- it is used downstream (see utils.clean_generated_text) to
    # truncate the model's continuation once it starts drifting into
    # irrelevant or repetitive text, mirroring the report's description of
    # a "predefined stopping point".
    prompt = f"{body_text}\n"
    return prompt


def build_fallback_closing(email_type: EmailType, sender_name: str = "") -> str:
    """
    Return the "closing + signature" block for a given email type.

    Used by `email_generator.py` as a post-processing safety net: if the
    model's raw continuation does not already contain a sign-off, this is
    appended so the final email always looks complete.
    """
    closing = _CLOSINGS.get(email_type, _DEFAULT_CLOSING)
    signature = sender_name.strip() if sender_name.strip() else "[Your Name]"
    return f"{closing}\n{signature}"


def get_supported_types():
    """Return the list of all supported EmailType values (for UI dropdowns)."""
    return list(EmailType)
