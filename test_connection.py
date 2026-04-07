import json
import os
from pathlib import Path

from aepp import configs, schema


def load_config(config_path: Path):
    with config_path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)

    scopes = raw_config.get("scopes") or os.getenv("AEP_SCOPES")
    sandbox = raw_config.get("sandbox-name") or raw_config.get("sandbox") or "prod"
    environment = raw_config.get("environment") or "prod"

    if not scopes:
        raise ValueError(
            "Missing OAuth scopes. Add a 'scopes' value in config/dev_config.json or set the AEP_SCOPES environment variable."
        )

    return configs.configure(
        org_id=raw_config.get("org_id"),
        client_id=raw_config.get("client_id") or raw_config.get("api_key"),
        secret=raw_config.get("secret") or raw_config.get("client_secret"),
        sandbox=sandbox,
        environment=environment,
        scopes=scopes,
        connectInstance=True,
    )

def run_test():
    try:
        config_path = Path(__file__).parent / "config" / "dev_config.json"
        config = load_config(config_path)

        schema_conn = schema.Schema(config=config)
        tenant_id = schema_conn.getTenantId()

        print("--- ✅ HANDSHAKE SUCCESSFUL ---")
        print(f"Connected to Sandbox: {schema_conn.sandbox}")
        print(f"Your Tenant ID: {tenant_id}")

    except Exception as e:
        print("--- ❌ STILL FAILING ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()