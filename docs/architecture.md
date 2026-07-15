# Architecture

## Overview

The Personalized Email Generator is a Streamlit application that uses
**GPT-Neo (1.3B)**, an open-source transformer language model from
EleutherAI, to draft complete, context-appropriate emails from a handful of
user-supplied fields (recipient, event/subject, extra instructions, email
type).

```
┌─────────────────────┐
│      app.py          │  Streamlit UI: collects form input, renders
│   (Presentation)     │  results, downloads, prompt preview.
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ email_generator.py    │  Orchestrates the pipeline:
│  (Orchestration)      │  validate -> build prompt -> generate -> clean
└─────┬─────┬─────┬─────┘
      │     │     │
      ▼     ▼     ▼
 validators prompt_  llm.py
   .py      templates (model backend)
            .py
                        │
                        ▼
              ┌────────────────────┐
              │  utils.py           │  Output cleaning: truncate at
              │ (Post-processing)   │  delimiter, dedupe lines, whitespace.
              └────────────────────┘
```

## Data Flow

1. **User Input** — The user fills in the Streamlit form: recipient name,
   email type, event/subject, optional extra instructions, and optional
   sender name.
2. **Validation** (`src/validators.py`) — Inputs are checked for
   completeness, length, and unsafe characters before any generation work
   begins.
3. **Prompt Engineering** (`src/prompt_templates.py`) — A structured prompt
   is built in the format:

   ```
   To: [Recipient]
   Subject: <type-specific subject>

   Dear [Recipient],
   I hope this message finds you well.
   <intent line derived from email type + event + extra info>
   ```

   Each `EmailType` (Professional, Leave Request, Job Application,
   Complaint, Thank You, Follow-up, Invitation, Formal, Informal) has its
   own subject prefix, salutation style, intent phrasing, and closing
   sign-off, so the same pipeline can produce very different tones from the
   same underlying model.

4. **Text Generation** (`src/llm.py`) — The prompt is tokenized and passed
   to GPT-Neo. Two backends are available:
   - **LocalGPTNeo**: loads `EleutherAI/gpt-neo-1.3B` via `transformers` +
     `torch` and runs generation in-process (CPU or GPU).
   - **InferenceAPIGPTNeo**: delegates generation to the Hugging Face
     Inference API using a token from `.env` (`HUGGINGFACEHUB_API_TOKEN`),
     for lightweight deployments.

   Generation uses sampling with tuned `temperature`, `top_k`, `top_p`,
   `repetition_penalty`, and `no_repeat_ngram_size` to balance creativity
   against coherence and avoid repetition — directly addressing the
   "Repetitive outputs" challenge described in the project report.

5. **Output Cleaning** (`src/utils.py`) — The raw continuation is:
   - Truncated at the `---` stop delimiter (or at the start of a
     hallucinated second "To:"/"Subject:" block).
   - De-duplicated line by line.
   - Whitespace-normalized.

6. **Post-processing** (`src/email_generator.py`) — If the cleaned output
   doesn't already contain a recognizable sign-off, a type-appropriate
   closing + signature is appended, guaranteeing a complete-looking email
   every time.

7. **Display** — The final email is rendered in a text area with word
   count, a "Download as .txt" button, and an expandable view of the exact
   prompt sent to the model (useful for debugging prompt engineering).

## Caching Strategy

Loading GPT-Neo's 1.3B parameters is the single most expensive operation in
the app. `app.py` wraps model instantiation in `@st.cache_resource`, and
`src/llm.py` additionally uses `functools.lru_cache` on `get_generator()`,
so the model is loaded at most once per process — regardless of how many
times a user clicks "Generate Email".

## Configuration

All tunable values (model name, generation hyperparameters, execution mode,
API tokens) are centralized in `src/config.py` and sourced from environment
variables / `.env`, never hardcoded. See `.env.example` for the full list.

## Extensibility

- **New email types**: add an entry to `EmailType` and the corresponding
  dictionaries in `src/prompt_templates.py`.
- **New model**: swap `MODEL_NAME`/`TOKENIZER_NAME` in `.env` — as long as
  the model is a causal LM compatible with `AutoModelForCausalLM`.
- **New backend** (e.g. OpenAI, Anthropic API): implement a class with a
  `.generate(prompt) -> str` method in `src/llm.py` and wire it into
  `get_generator()`.
