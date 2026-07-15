"""
app.py
------
Streamlit UI for the Personalized Email Generator (GPT-Neo 1.3B).

Run with:
    streamlit run app.py

This file is intentionally kept thin -- all business logic lives in the
`src/` package (email_generator, prompt_templates, llm, utils, validators,
config). `app.py` is only responsible for layout and user interaction.
"""

import logging

import streamlit as st

from src.config import settings
from src.email_generator import EmailGenerator
from src.prompt_templates import EmailType, EMAIL_TYPE_DESCRIPTIONS, get_supported_types
from src.utils import to_downloadable_filename

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title=settings.APP_TITLE,
    page_icon=settings.APP_ICON,
    layout="centered",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------
# Cached resources
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_generator() -> EmailGenerator:
    """
    Cache the EmailGenerator (and, transitively, the GPT-Neo model) across
    reruns so the ~1.3B parameter model is only loaded once per session,
    exactly as described in the report's "Slow performance" solution
    (`@st.cache_resource`).
    """
    return EmailGenerator()


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## {settings.APP_ICON} {settings.APP_TITLE}")
    st.markdown(
        "An AI-powered tool that drafts complete, professional emails "
        "from just a few details, using **GPT-Neo (1.3B)**."
    )
    st.divider()

    st.markdown("### ⚙️ Generation Settings")
    st.caption(
        "These map directly to GPT-Neo's generation parameters "
        "(temperature, top-k, top-p, repetition penalty)."
    )
    st.write(f"**Model:** `{settings.MODEL_NAME}`")
    st.write(f"**Max new tokens:** {settings.MAX_NEW_TOKENS}")
    st.write(f"**Temperature:** {settings.TEMPERATURE}")
    st.write(f"**Top-k / Top-p:** {settings.TOP_K} / {settings.TOP_P}")
    st.write(f"**Repetition penalty:** {settings.REPETITION_PENALTY}")

    st.divider()
    st.caption(
        "Built for the *Personalized Email Generator using GPT-Neo* "
        "project. See `docs/architecture.md` for design details."
    )


# --------------------------------------------------------------------------
# Main layout
# --------------------------------------------------------------------------
st.title(f"{settings.APP_ICON} {settings.APP_TITLE}")
st.write(
    "Fill in a few details below and let GPT-Neo draft a complete, "
    "well-structured email for you."
)

with st.form("email_form"):
    col1, col2 = st.columns(2)

    with col1:
        recipient = st.text_input(
            "Recipient's Name *",
            placeholder="e.g. Dr. Mehta",
            help="Who is this email addressed to?",
        )
    with col2:
        sender_name = st.text_input(
            "Your Name (optional)",
            placeholder="e.g. Aditi Sinharoy",
            help="Used to sign off the email. Defaults to '[Your Name]'.",
        )

    email_type_label = st.selectbox(
        "Email Type *",
        options=[t.value for t in get_supported_types()],
        index=[t.value for t in get_supported_types()].index(EmailType.INVITATION.value),
        help="Choose the kind of email you want to generate.",
    )
    selected_type = EmailType(email_type_label)
    st.caption(EMAIL_TYPE_DESCRIPTIONS[selected_type])

    event = st.text_input(
        "Event / Subject *",
        placeholder="e.g. AI Summit 2025",
        help="The occasion, topic, or reason for the email.",
    )

    extra_info = st.text_area(
        "Additional Instructions (optional)",
        placeholder="e.g. It will start at 10 AM and feature sessions on Responsible AI.",
        help="Any extra details you'd like included in the email body.",
        height=100,
    )

    submitted = st.form_submit_button("✉️ Generate Email", use_container_width=True)

if submitted:
    if not recipient.strip() or not event.strip():
        st.warning("⚠️ Please fill in both the recipient's name and the event/subject.")
    else:
        with st.spinner("Generating your email with GPT-Neo... this may take a moment."):
            try:
                generator = load_generator()
                result = generator.generate(
                    email_type=selected_type,
                    recipient=recipient,
                    event=event,
                    extra_info=extra_info,
                    sender_name=sender_name,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(
                    "❌ Failed to load or run the GPT-Neo model. "
                    f"Details: {exc}"
                )
                result = None

        if result is not None:
            if result.success:
                st.success("✅ Email generated successfully!")
                st.text_area(
                    "Generated Email",
                    value=result.email_text,
                    height=320,
                )
                st.caption(f"📝 {result.word_count} words")

                st.download_button(
                    label="⬇️ Download as .txt",
                    data=result.email_text,
                    file_name=to_downloadable_filename(recipient, event),
                    mime="text/plain",
                    use_container_width=True,
                )

                with st.expander("🔍 View the prompt sent to GPT-Neo"):
                    st.code(result.prompt_used, language="text")
            else:
                st.error(f"❌ {result.error}")

st.divider()
st.caption(
    "Powered by [GPT-Neo (1.3B)](https://huggingface.co/EleutherAI/gpt-neo-1.3B) "
    "from EleutherAI, via Hugging Face Transformers and Streamlit."
)
