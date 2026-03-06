"""
License Manager — Online validation via PISKU server.
Caches result in config.json to allow offline use after first validation.
"""
import json
import hashlib
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


CONFIG_FILE = "config/config.json"
SERVER_URL_KEY = "server_url"
DEFAULT_SERVER = "http://localhost:8000"  # Change to production URL


class LicenseManager:
    def __init__(self, root: Path):
        self.root = root
        self.config_path = root / CONFIG_FILE
        self._config: Optional[dict] = None

    def _load_config(self) -> dict:
        if self._config is None:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    self._config = json.load(f)
            else:
                self._config = self._default_config()
                self._save_config()
        return self._config

    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def _default_config(self) -> dict:
        return {
            "tier": "free",
            "license_key": None,
            "license_hash": None,
            "activated_at": None,
            "expires_at": None,
            "last_validated": None,
            SERVER_URL_KEY: DEFAULT_SERVER,
        }

    def is_pro(self) -> bool:
        config = self._load_config()
        if config["tier"] != "pro":
            return False

        # Check expiry from cached data
        expires = config.get("expires_at")
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires)
                if datetime.now() > exp_dt:
                    # Expired — downgrade silently
                    self._downgrade()
                    return False
            except ValueError:
                pass

        return True

    def _downgrade(self):
        config = self._load_config()
        config["tier"] = "free"
        config["license_key"] = None
        config["license_hash"] = None
        self._save_config()

    def activate(self, license_key: str) -> dict:
        """Validate key against PISKU server and cache result."""
        config = self._load_config()
        server = config.get(SERVER_URL_KEY, DEFAULT_SERVER)

        try:
            response = httpx.post(
                f"{server}/api/licenses/validate",
                json={"key": license_key},
                timeout=10.0,
            )
            data = response.json()
        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"Cannot reach PISKU server at {server}. Check your connection or server URL."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

        if data.get("valid"):
            key_hash = hashlib.sha256(license_key.encode()).hexdigest()
            config["tier"] = "pro"
            config["license_key"] = license_key[:8] + "..." + license_key[-4:]
            config["license_hash"] = key_hash
            config["activated_at"] = datetime.now().isoformat()
            config["expires_at"] = data.get("expires_at")
            config["last_validated"] = datetime.now().isoformat()
            self._save_config()
            return {"success": True, "expires": data.get("expires_at")}
        else:
            return {"success": False, "error": data.get("error", "Invalid license key")}

    def get_server_url(self) -> str:
        return self._load_config().get(SERVER_URL_KEY, DEFAULT_SERVER)

    def set_server_url(self, url: str):
        config = self._load_config()
        config[SERVER_URL_KEY] = url
        self._save_config()
