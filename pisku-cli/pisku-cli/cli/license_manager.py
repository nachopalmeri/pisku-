"""
License Manager — Online validation via PISKU server.
Caches result in config/config.json to allow offline use after first validation.

Server URL resolution order:
  1. Environment variable PISKU_SERVER_URL  (overrides everything — for self-hosted / dev)
  2. Value stored in config/config.json      (set once at install or via `pisku config`)
  3. DEFAULT_SERVER                          (production Railway URL, hardcoded fallback)
"""
import json
import os
import hashlib
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional

CONFIG_FILE      = "config/config.json"
SERVER_URL_KEY   = "server_url"
DEFAULT_SERVER   = "https://pisku-production.up.railway.app"   # ← production
ENV_SERVER_KEY   = "PISKU_SERVER_URL"                           # env var override


class LicenseManager:
    def __init__(self, root: Path):
        self.root = root
        self.config_path = root / CONFIG_FILE
        self._config: Optional[dict] = None

    # ── Config I/O ───────────────────────────────────────────────────

    def _load_config(self) -> dict:
        if self._config is None:
            if self.config_path.exists():
                try:
                    with open(self.config_path, encoding="utf-8") as f:
                        self._config = json.load(f)
                except (json.JSONDecodeError, OSError):
                    self._config = self._default_config()
                    self._save_config()
            else:
                self._config = self._default_config()
                self._save_config()
        return self._config

    def _save_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def _default_config(self) -> dict:
        return {
            "tier":           "free",
            "license_key":    None,
            "license_hash":   None,
            "activated_at":   None,
            "expires_at":     None,
            "last_validated": None,
            SERVER_URL_KEY:   DEFAULT_SERVER,
        }

    # ── Server URL resolution ─────────────────────────────────────────

    def get_server_url(self) -> str:
        """
        Resolve server URL with priority:
          1. PISKU_SERVER_URL env var   (dev / self-hosted override)
          2. config/config.json value
          3. DEFAULT_SERVER (Railway production)
        """
        env_url = os.environ.get(ENV_SERVER_KEY, "").strip()
        if env_url:
            return env_url.rstrip("/")
        stored = self._load_config().get(SERVER_URL_KEY, DEFAULT_SERVER)
        return (stored or DEFAULT_SERVER).rstrip("/")

    def set_server_url(self, url: str) -> None:
        config = self._load_config()
        config[SERVER_URL_KEY] = url.rstrip("/")
        self._save_config()

    # ── Tier checks ───────────────────────────────────────────────────

    def is_pro(self) -> bool:
        config = self._load_config()
        if config.get("tier") != "pro":
            return False

        expires = config.get("expires_at")
        if expires and expires != "lifetime":
            try:
                if datetime.now() > datetime.fromisoformat(expires):
                    self._downgrade()
                    return False
            except (ValueError, TypeError):
                pass   # malformed date → treat as non-expired

        return True

    def _downgrade(self) -> None:
        config = self._load_config()
        config["tier"]         = "free"
        config["license_key"]  = None
        config["license_hash"] = None
        self._save_config()

    # ── Activation ───────────────────────────────────────────────────

    def activate(self, license_key: str) -> dict:
        """
        Validate key against PISKU server and cache the result locally.
        After the first successful activation the CLI works fully offline.
        """
        server = self.get_server_url()
        endpoint = f"{server}/api/licenses/validate"

        try:
            response = httpx.post(
                endpoint,
                json={"key": license_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": (
                    f"Cannot reach PISKU server at {server}.\n"
                    f"  • Check your internet connection\n"
                    f"  • Or set PISKU_SERVER_URL env var for a local server"
                ),
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"Server error {e.response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

        if data.get("valid"):
            config = self._load_config()
            key_hash = hashlib.sha256(license_key.encode()).hexdigest()
            expires  = data.get("expires_at", "lifetime")

            config["tier"]           = "pro"
            config["license_key"]    = license_key[:8] + "..." + license_key[-4:]
            config["license_hash"]   = key_hash
            config["activated_at"]   = datetime.now().isoformat()
            config["expires_at"]     = expires
            config["last_validated"] = datetime.now().isoformat()
            self._config = config
            self._save_config()

            return {"success": True, "expires": expires}

        return {
            "success": False,
            "error": data.get("error", "Invalid or unknown license key"),
        }
