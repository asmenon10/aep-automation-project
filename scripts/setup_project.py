from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / "venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "dev_config.json"


def run(command: list[str]) -> None:
    print(f"\n> {' '.join(command)}")
    subprocess.run(command, check=True)


def create_venv() -> None:
    if VENV_DIR.exists():
        print(f"Virtual environment already exists at {VENV_DIR}")
        return

    print(f"Creating virtual environment at {VENV_DIR}...")
    run([sys.executable, "-m", "venv", str(VENV_DIR)])


def venv_python() -> Path:
    if platform.system().lower().startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def install_requirements() -> None:
    python_executable = venv_python()

    if not python_executable.exists():
        raise FileNotFoundError(
            f"Virtual environment Python not found at {python_executable}"
        )

    print("Installing project dependencies...")
    run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python_executable), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])


def ensure_config_folder() -> None:
    CONFIG_DIR.mkdir(exist_ok=True)

    if CONFIG_FILE.exists():
        print(f"Config file already exists at {CONFIG_FILE}")
        return

    template = """{
  \"org_id\": \"YOUR_ORG_ID@AdobeOrg\",
  \"client_id\": \"YOUR_CLIENT_ID\",
  \"secret\": \"YOUR_CLIENT_SECRET\",
  \"sandbox-name\": \"prod\",
  \"environment\": \"prod\",
  \"scopes\": \"openid,AdobeID,read_organizations\"
}
"""
    CONFIG_FILE.write_text(template, encoding="utf-8")
    print(f"Created config template at {CONFIG_FILE}")


def print_next_steps() -> None:
    if platform.system().lower().startswith("win"):
        activate_command = r"venv\Scripts\activate"
    else:
        activate_command = "source venv/bin/activate"

    print("\nSetup complete.")
    print("Next steps:")
    print(f"1. Activate the virtual environment: {activate_command}")
    print(f"2. Update {CONFIG_FILE.relative_to(PROJECT_ROOT)} with your Adobe credentials")
    print("3. Run the connection test: python test_connection.py")


def main() -> None:
    print(f"Project root: {PROJECT_ROOT}")

    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"requirements.txt not found at {REQUIREMENTS_FILE}")

    create_venv()
    install_requirements()
    ensure_config_folder()
    print_next_steps()


if __name__ == "__main__":
    main()
