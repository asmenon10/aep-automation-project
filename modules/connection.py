"""
Centralized AEP connection manager.
Every module imports from here. Never authenticate inline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aepp


_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_config(environment: str = "dev") -> dict[str, Any]:
    """Load credentials from config/<environment>_config.json."""
    config_path = _CONFIG_DIR / f"{environment}_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {config_path}\n"
            f"Run setup_project.py first or create the file manually."
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


def connect(environment: str = "dev", sandbox: str | None = None) -> dict[str, Any]:
    """Authenticate to AEP and return the config used."""
    config = load_config(environment)

    aepp.configure(
        org_id=config["org_id"],
        client_id=config["client_id"],
        secret=config["secret"],
        sandbox=sandbox or config.get("sandbox-name", "prod"),
        scopes=config.get("scopes", "openid,AdobeID,read_organizations"),
    )

    active_sandbox = sandbox or config.get("sandbox-name", "prod")
    print(f"  ✅ Connected to [{environment}] sandbox: {active_sandbox}")
    return config