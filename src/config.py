"""Central config. Loads .env and exposes keys, base URLs, and model names.

Keys are NEVER hardcoded — they come from .env (gitignored). Models and base
URLs are overridable via env so we can swap them without touching code.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- API keys (from .env) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
# Optional: a server (guild) id makes slash commands sync instantly for testing.
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
# Plain-text messages (vs only the /stock slash command) need Discord's
# privileged "Message Content Intent" enabled in the Developer Portal. Opt in
# here only after enabling it there, or the bot login will fail.
DISCORD_MESSAGE_CONTENT = os.getenv("DISCORD_MESSAGE_CONTENT", "").strip().lower() in (
    "1", "true", "yes", "on",
)

# --- Email fallback (SMTP; defaults suit Gmail with an app password) ---
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com").strip()
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "").strip()        # sender / SMTP login
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").strip()
EMAIL_TO = os.getenv("EMAIL_TO", "").strip() or EMAIL_ADDRESS  # recipient

# --- OpenAI-compatible endpoints ---
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
NVIDIA_NIM_BASE_URL = os.getenv(
    "NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"
)

# --- Models. Groq is primary, NVIDIA NIM is the fallback. ---
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")

# --- Per-agent model overrides ---
# Each agent (the three workers, the two debaters, the judge) can run on its own
# Groq model. Leave an override blank in .env to use GROQ_MODEL. The NVIDIA NIM
# fallback model stays shared (NVIDIA_NIM_MODEL) for every agent.
_AGENT_MODEL_ENV = {
    "technicals": "MODEL_TECHNICALS",
    "fundamentals": "MODEL_FUNDAMENTALS",
    "news": "MODEL_NEWS",
    "bull": "MODEL_BULL",
    "bear": "MODEL_BEAR",
    "judge": "MODEL_JUDGE",
}


def model_for(role: str) -> str:
    """Groq model id for an agent role; falls back to GROQ_MODEL when unset."""
    env_var = _AGENT_MODEL_ENV.get(role)
    if env_var:
        override = os.getenv(env_var, "").strip()
        if override:
            return override
    return GROQ_MODEL
