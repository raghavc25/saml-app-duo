import os

from config_store import get_config


def _read_file(path):
    if not path:
        return ""
    with open(path, "r") as f:
        return f.read().strip()


def _clean_cert(raw):
    """Accept a cert pasted with or without PEM header/footer/newlines."""
    lines = [line.strip() for line in raw.strip().splitlines()]
    body = [line for line in lines if line and not line.startswith("-----")]
    return "".join(body)


def get_saml_settings():
    """Build a python3-saml settings dict from the saved SAML config (editable
    via the /admin UI) plus a couple of process-level env vars for local SP
    request signing, which stays file-based."""

    cfg = get_config()

    sp_cert = _read_file(os.environ.get("SP_CERT_FILE", ""))
    sp_key = _read_file(os.environ.get("SP_KEY_FILE", ""))
    authn_requests_signed = bool(sp_cert and sp_key)

    idp_cert = _clean_cert(cfg["idp_x509_cert"])

    return {
        "strict": True,
        "debug": os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        "sp": {
            "entityId": cfg["sp_entity_id"],
            "assertionConsumerService": {
                "url": cfg["sp_acs_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": cfg["sp_sls_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": sp_cert,
            "privateKey": sp_key,
        },
        "idp": {
            "entityId": cfg["idp_entity_id"],
            "singleSignOnService": {
                "url": cfg["idp_sso_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": cfg["idp_sls_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": idp_cert,
        },
        "security": {
            "authnRequestsSigned": authn_requests_signed,
            "logoutRequestSigned": authn_requests_signed,
            "logoutResponseSigned": authn_requests_signed,
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "wantNameId": True,
            "signMetadata": authn_requests_signed,
        },
    }
