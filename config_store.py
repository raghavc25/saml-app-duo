import json
import os
import threading
from pathlib import Path

CONFIG_DIR = Path(__file__).parent / "instance"
CONFIG_FILE = CONFIG_DIR / "saml_settings.json"

FIELDS = [
    "sp_entity_id",
    "sp_acs_url",
    "sp_sls_url",
    "idp_entity_id",
    "idp_sso_url",
    "idp_sls_url",
    "idp_x509_cert",
]

_lock = threading.Lock()


def _defaults():
    """Seed values on first run, coming from .env so existing setups keep working."""
    return {
        "sp_entity_id": os.environ.get("SP_ENTITY_ID", "http://localhost:5000/saml/metadata"),
        "sp_acs_url": os.environ.get("SP_ACS_URL", "http://localhost:5000/saml/acs"),
        "sp_sls_url": os.environ.get("SP_SLS_URL", "http://localhost:5000/saml/sls"),
        "idp_entity_id": os.environ.get("IDP_ENTITY_ID", ""),
        "idp_sso_url": os.environ.get("IDP_SSO_URL", ""),
        "idp_sls_url": os.environ.get("IDP_SLS_URL", ""),
        "idp_x509_cert": os.environ.get("IDP_X509_CERT", ""),
    }


def _get_config_locked():
    if CONFIG_FILE.exists():
        saved = json.loads(CONFIG_FILE.read_text())
        merged = _defaults()
        merged.update({k: v for k, v in saved.items() if k in FIELDS})
        return merged
    return _defaults()


def get_config():
    with _lock:
        return _get_config_locked()


def save_config(new_values):
    with _lock:
        current = _get_config_locked()
        current.update({k: (new_values.get(k) or "").strip() for k in FIELDS if k in new_values})
        CONFIG_DIR.mkdir(exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(current, indent=2))
        return current
