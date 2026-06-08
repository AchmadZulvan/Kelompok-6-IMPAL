import os
from pathlib import Path

from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore


# Load environment variables from .env (if present)
load_dotenv()


def _resolve_service_account_path() -> str:
    """Resolve the Firebase service account JSON path.

    Priority:
    1) FIREBASE_SERVICE_ACCOUNT_PATH env var
    2) Default JSON in project root (current repo already includes it)
    """

    env_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if env_path:
        return env_path

    # Fallback: the JSON that currently exists in this project
    project_root = Path(__file__).resolve().parent
    fallback = project_root / "simobs-bengkel-firebase-adminsdk-fbsvc-8a002d20de.json"
    return str(fallback)


_SERVICE_ACCOUNT_PATH = _resolve_service_account_path()

if not firebase_admin._apps:
    if not os.path.exists(_SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(
            "Firebase service account JSON tidak ditemukan. "
            "Set env FIREBASE_SERVICE_ACCOUNT_PATH (lihat file .env) atau letakkan file JSON di root project. "
            f"Path yang dicoba: {_SERVICE_ACCOUNT_PATH}"
        )

    cred = credentials.Certificate(_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)


# Firestore client
db = firestore.client()
