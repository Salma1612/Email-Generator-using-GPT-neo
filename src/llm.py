"""
llm.py
------
Thin wrapper around GPT-Neo (EleutherAI/gpt-neo-1.3B), matching the
"Model Loading" and "Text Generation" steps from the project report.

Two backends are supported:

* LocalGPTNeo   - loads the model + tokenizer in-process with
                  `transformers` + `torch` (the exact approach used in the
                  report).
* InferenceAPIGPTNeo - calls the Hugging Face Inference API instead,
                  so the app can run without downloading the full model.
                  Requires HUGGINGFACEHUB_API_TOKEN to be set.

`get_generator()` returns whichever backend is configured via
`settings.USE_INFERENCE_API`, and is cached so the (potentially expensive)
model load only happens once per process -- mirroring the report's use of
`@st.cache_resource` to avoid reloading GPT-Neo on every interaction.
"""

import functools
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class GenerationError(RuntimeError):
    """Raised when text generation fails for any reason (model, network, etc.)."""


class LocalGPTNeo:
    """
    Runs GPT-Neo 1.3B locally via Hugging Face `transformers`.

    This mirrors the report's methodology exactly:
      - AutoModelForCausalLM + AutoTokenizer from 'EleutherAI/gpt-neo-1.3B'
      - pad_token set to eos_token to avoid generation errors
      - temperature / top_k / top_p / repetition_penalty tuned for quality
    """

    def __init__(self):
        # Imports are deferred so that `torch`/`transformers` are only
        # required if this backend is actually used.
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch

        logger.info("Loading tokenizer '%s'...", settings.TOKENIZER_NAME)
        self.tokenizer = AutoTokenizer.from_pretrained(settings.TOKENIZER_NAME)

        # GPT-Neo's tokenizer (GPT-2 based) has no pad token by default.
        # Setting it to eos_token prevents "Asking to pad but the tokenizer
        # does not have a padding token" errors during generation.
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        logger.info("Loading model '%s'...", settings.MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(settings.MODEL_NAME)

        if settings.DEVICE == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = settings.DEVICE

        self.model.to(self.device)
        self.model.eval()
        logger.info("GPT-Neo loaded on device: %s", self.device)

    def generate(self, prompt: str) -> str:
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            with self._torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=settings.MAX_NEW_TOKENS,
                    do_sample=True,
                    temperature=settings.TEMPERATURE,
                    top_k=settings.TOP_K,
                    top_p=settings.TOP_P,
                    repetition_penalty=settings.REPETITION_PENALTY,
                    no_repeat_ngram_size=settings.NO_REPEAT_NGRAM_SIZE,
                    pad_token_id=self.tokenizer.pad_token_id,
                )

            full_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

            # Only return the newly generated continuation, not the echoed
            # prompt, so downstream cleaning works on the model's output.
            continuation = full_text[len(prompt):]
            return continuation
        except Exception as exc:  # noqa: BLE001 - surfaced as GenerationError
            logger.exception("Local generation failed")
            raise GenerationError(f"Local model generation failed: {exc}") from exc


class InferenceAPIGPTNeo:
    """
    Calls the Hugging Face Inference API for text generation instead of
    loading the model locally. Requires `HUGGINGFACEHUB_API_TOKEN`.
    """

    API_URL = f"https://api-inference.huggingface.co/models/{settings.MODEL_NAME}"

    def __init__(self):
        if not settings.HUGGINGFACEHUB_API_TOKEN:
            raise GenerationError(
                "USE_INFERENCE_API is enabled but HUGGINGFACEHUB_API_TOKEN "
                "is not set. Add it to your .env file."
            )
        self._token = settings.HUGGINGFACEHUB_API_TOKEN

    def generate(self, prompt: str) -> str:
        import requests

        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": settings.MAX_NEW_TOKENS,
                "temperature": settings.TEMPERATURE,
                "top_k": settings.TOP_K,
                "top_p": settings.TOP_P,
                "repetition_penalty": settings.REPETITION_PENALTY,
                "return_full_text": False,
            },
            "options": {"wait_for_model": True},
        }

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Inference API request failed")
            raise GenerationError(f"Inference API request failed: {exc}") from exc

        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"]
        if isinstance(data, dict) and "error" in data:
            raise GenerationError(f"Inference API error: {data['error']}")

        raise GenerationError(f"Unexpected Inference API response: {data}")


@functools.lru_cache(maxsize=1)
def get_generator():
    """
    Return a cached generator instance (either local or Inference API
    backed, depending on configuration). Cached with `lru_cache` so the
    expensive model load happens only once per process -- the equivalent
    of the report's `@st.cache_resource` decorator.
    """
    if settings.USE_INFERENCE_API:
        logger.info("Using Hugging Face Inference API backend for GPT-Neo.")
        return InferenceAPIGPTNeo()

    logger.info("Using local GPT-Neo backend.")
    return LocalGPTNeo()
