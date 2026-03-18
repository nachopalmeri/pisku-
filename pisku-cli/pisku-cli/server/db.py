"""
DB — Simple JSON file store para licencias.
Suficiente para portafolio. Si escala, swapeá por Supabase.

Schema de licenses.json:
{
  "licenses": {
    "<key>": {
      "key": str,
      "email": str,
      "active": bool,
      "stripe_session_id": str | null,
      "plan": "monthly" | "yearly",
      "created_at": ISO str,
      "expires_at": ISO str
    }
  }
}
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from server.config import settings

DB_PATH = Path(__file__).parent.parent / "config" / "licenses.json"


def init_db():
    """Crea el archivo si no existe y agrega la key de demo."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        _write({"licenses": {}})

    # Siempre asegurar que la demo key existe
    data = _read()
    demo_key = settings.demo_license_key
    if demo_key not in data["licenses"]:
        data["licenses"][demo_key] = {
            "key": demo_key,
            "email": "demo@pisku.dev",
            "active": True,
            "stripe_session_id": None,
            "plan": "monthly",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        }
        _write(data)
        print(f"  Demo key seeded: {demo_key}")


def _read() -> dict:
    with open(DB_PATH) as f:
        return json.load(f)


def _write(data: dict):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_license(key: str) -> Optional[dict]:
    data = _read()
    return data["licenses"].get(key)


def create_license(
    key: str,
    email: str,
    plan: str,
    stripe_session_id: Optional[str] = None,
) -> dict:
    data = _read()
    days = 365 if plan == "yearly" else settings.license_duration_days
    license_record = {
        "key": key,
        "email": email,
        "active": True,
        "stripe_session_id": stripe_session_id,
        "plan": plan,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=days)).isoformat(),
    }
    data["licenses"][key] = license_record
    _write(data)
    return license_record


def deactivate_license(key: str):
    data = _read()
    if key in data["licenses"]:
        data["licenses"][key]["active"] = False
        _write(data)


def get_by_stripe_session(session_id: str) -> Optional[dict]:
    data = _read()
    for lic in data["licenses"].values():
        if lic.get("stripe_session_id") == session_id:
            return lic
    return None
