"""Leitura das configuracoes a partir do arquivo .env (nunca versionado)."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent


def carregar_config():
    load_dotenv(RAIZ / ".env")
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY", ""),
        "DB_HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "DB_PORT": int(os.environ.get("DB_PORT", "5432") or 5432),
        "DB_NAME": os.environ.get("DB_NAME", "dgp"),
        "DB_USER": os.environ.get("DB_USER", "dgp_app"),
        "DB_PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "VALIDAR_DIGITO_DOCUMENTO": os.environ.get("VALIDAR_DIGITO_DOCUMENTO", "1") == "1",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=8),
        "MAX_CONTENT_LENGTH": 1024 * 1024,
    }
