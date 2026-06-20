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

# --- OpenAI-compatible endpoints ---
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
NVIDIA_NIM_BASE_URL = os.getenv(
    "NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"
)

# --- Models. Groq is primary, NVIDIA NIM is the fallback. ---
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")
