"""LLM factory: Groq primary, NVIDIA NIM fallback, both OpenAI-compatible.

`build_structured_llm(schema)` returns a runnable that emits validated instances
of `schema`. If Groq fails (rate limit, outage), LangChain transparently retries
the same call against NVIDIA NIM.
"""

from langchain_openai import ChatOpenAI

from . import config


def _provider_llm(provider: str):
    """Build a ChatOpenAI for one provider, or None if its key is missing."""
    if provider == "groq":
        if not config.GROQ_API_KEY:
            return None
        return ChatOpenAI(
            model=config.GROQ_MODEL,
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
            model=config.NVIDIA_NIM_MODEL,
            api_key=config.NVIDIA_NIM_API_KEY,
            base_url=config.NVIDIA_NIM_BASE_URL,
            temperature=0,
            timeout=60,
            max_retries=2,
        )
    raise ValueError(f"unknown provider {provider!r}")


def build_structured_llm(schema):
    """Return a runnable that outputs validated `schema` objects, with fallback.

    Groq is tried first; NVIDIA NIM backs it up. Each provider is wrapped in
    `with_structured_output` so both return the strict shape.
    """
    structured = []
    for provider in ("groq", "nim"):
        llm = _provider_llm(provider)
        if llm is not None:
            structured.append(llm.with_structured_output(schema))

    if not structured:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY (and optionally "
            "NVIDIA_NIM_API_KEY) in your .env."
        )

    primary, *backups = structured
    return primary.with_fallbacks(backups) if backups else primary


def build_chat_llm():
    """Return a plain chat runnable (free-text output), Groq + NIM fallback.

    Used by the Bull/Bear debaters, who argue in prose rather than strict JSON.
    """
    llms = []
    for provider in ("groq", "nim"):
        llm = _provider_llm(provider)
        if llm is not None:
            llms.append(llm)

    if not llms:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY (and optionally "
            "NVIDIA_NIM_API_KEY) in your .env."
        )

    primary, *backups = llms
    return primary.with_fallbacks(backups) if backups else primary
