# config.py
import yaml
from pathlib import Path
import os
from dotenv import load_dotenv


def load_yaml_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_email_env() -> dict:
    load_dotenv()

    return {
        "smtp_server": os.getenv("EMAIL_SMTP_SERVER"),
        "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
        "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
        "username": os.getenv("EMAIL_USERNAME"),
        "password": os.getenv("EMAIL_PASSWORD"),
        "from_addr": os.getenv("EMAIL_FROM"),
        "to_addrs": [
            addr.strip()
            for addr in os.getenv("EMAIL_TO", "").split(",")
            if addr.strip()
        ],
    }
