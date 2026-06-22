"""The AI factory — one place that builds every connection to an LLM.

Every agent gets its AI from here, so the "how do we talk to the model" details
live in exactly one file. Two flavours:

  - build_structured_llm(Schema) : the AI is FORCED to answer in a Pydantic shape
    (used by the workers and the judge, which need strict JSON).
  - build_chat_llm()             : the AI answers in plain prose
    (used by the Bull/Bear debaters, who write arguments).

Both wire up a SAFETY NET: try Groq first; if Groq fails (rate limit, outage),
LangChain automatically retries the SAME request on NVIDIA NIM. The caller never
has to think about it.

("OpenAI-compatible" just means Groq and NIM both speak the same API dialect, so
the same ChatOpenAI client works for either by swapping the base URL + key.)
"""

from langchain_openai import ChatOpenAI

from . import config


def _provider_llm(provider: str, model: str | None = None):
    """Build a ChatOpenAI for one provider, or None if its key is missing.

    `model` overrides the provider's default model when given.
    """
    if provider == "groq":
        if not config.GROQ_API_KEY:
            return None
        return ChatOpenAI(
            model=model or config.GROQ_MODEL,
            api_key=config.GROQ_API_KEY,
            base_url=config.GROQ_BASE_URL,
            temperature=0,
            timeout=60,
            max_retries=2,
        )
    if provider == "nim":
        if not config.NVIDIA_NIM_API_KEY:
            return None
        return ChatOpenAI(
            model=model or config.NVIDIA_NIM_MODEL,
            api_key=config.NVIDIA_NIM_API_KEY,
            base_url=config.NVIDIA_NIM_BASE_URL,
            temperature=0,
            timeout=60,
            max_retries=2,
        )
    raise ValueError(f"unknown provider {provider!r}")


def build_structured_llm(schema, model: str | None = None, fallback_model: str | None = None):
    """Return a runnable that outputs validated `schema` objects, with fallback.

    Groq (model `model` or default) is tried first; NVIDIA NIM backs it up. Each
    provider is wrapped in `with_structured_output` so both return the strict shape.
    """
    structured = []
    for provider, m in (("groq", model), ("nim", fallback_model)):
        llm = _provider_llm(provider, m)
        if llm is not None:
            structured.append(llm.with_structured_output(schema))

    if not structured:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY (and optionally "
            "NVIDIA_NIM_API_KEY) in your .env."
        )

    primary, *backups = structured
    return primary.with_fallbacks(backups) if backups else primary


def build_chat_llm(model: str | None = None, fallback_model: str | None = None):
    """Return a plain chat runnable (free-text output), Groq + NIM fallback.

    Used by the Bull/Bear debaters, who argue in prose rather than strict JSON.
    """
    llms = []
    for provider, m in (("groq", model), ("nim", fallback_model)):
        llm = _provider_llm(provider, m)
        if llm is not None:
            llms.append(llm)

    if not llms:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY (and optionally "
            "NVIDIA_NIM_API_KEY) in your .env."
        )

    primary, *backups = llms
    return primary.with_fallbacks(backups) if backups else primary
