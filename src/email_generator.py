"""
email_generator.py
-------------------
High-level orchestration layer that ties together:
  1. Input validation           (src/validators.py)
  2. Prompt engineering         (src/prompt_templates.py)
  3. GPT-Neo text generation    (src/llm.py)
  4. Output cleaning            (src/utils.py)

This is the single entry point the UI (`app.py`) should call.
"""

import logging
from dataclasses import dataclass

from src.llm import get_generator, GenerationError
from src.prompt_templates import EmailType, build_prompt, build_fallback_closing
from src.utils import clean_generated_text, word_count
from src.validators import validate_email_request

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Structured result returned to the UI layer."""

    success: bool
    email_text: str = ""
    prompt_used: str = ""
    error: str = ""
    word_count: int = 0


class EmailGenerator:
    """
    Facade class for generating a personalized email end-to-end.

    Example
    -------
    >>> generator = EmailGenerator()
    >>> result = generator.generate(
    ...     email_type=EmailType.INVITATION,
    ...     recipient="Dr. Mehta",
    ...     event="AI Summit 2025",
    ...     extra_info="It will start at 10 AM and feature sessions on Responsible AI.",
    ... )
    >>> print(result.email_text)
    """

    def generate(
        self,
        email_type: EmailType,
        recipient: str,
        event: str,
        extra_info: str = "",
        sender_name: str = "",
    ) -> EmailResult:
        # 1. Validate inputs before doing any expensive work.
        validation = validate_email_request(recipient, event, extra_info, sender_name)
        if not validation.is_valid:
            return EmailResult(success=False, error=" ".join(validation.errors))

        # 2. Build the structured prompt.
        prompt = build_prompt(
            email_type=email_type,
            recipient=recipient,
            event=event,
            extra_info=extra_info,
            sender_name=sender_name,
        )

        # 3. Generate text with GPT-Neo (local model or Inference API).
        try:
            generator = get_generator()
            raw_output = generator.generate(prompt)
        except GenerationError as exc:
            logger.error("Generation failed: %s", exc)
            return EmailResult(
                success=False,
                error=(
                    "The email could not be generated right now. "
                    f"Details: {exc}"
                ),
                prompt_used=prompt,
            )
        except Exception as exc:  # noqa: BLE001 - final safety net
            logger.exception("Unexpected error during generation")
            return EmailResult(
                success=False,
                error=f"An unexpected error occurred: {exc}",
                prompt_used=prompt,
            )

        # 4. Clean the raw output (truncate at delimiter, dedupe lines).
        cleaned = clean_generated_text(raw_output)

        # 5. Assemble the final displayed email: prompt header (To/Subject/
        #    greeting) + model continuation, with a fallback closing if the
        #    model didn't produce one.
        header = prompt.rstrip("\n")
        # Join with a single space so the model's continuation reads as a
        # natural extension of the prompt's final line, regardless of
        # whether the cleaning pipeline stripped the model's own leading
        # whitespace.
        full_email = f"{header} {cleaned}".strip()

        if not any(
            keyword in full_email.lower()
            for keyword in ("regards", "sincerely", "thanks", "thank you", "best,")
        ):
            full_email += "\n\n" + build_fallback_closing(email_type, sender_name)

        return EmailResult(
            success=True,
            email_text=full_email,
            prompt_used=prompt,
            word_count=word_count(full_email),
        )
