import os


def _read_file(path):
    if not path:
        return ""
    with open(path, "r") as f:
        return f.read().strip()


def get_saml_settings():
    """Build a python3-saml settings dict entirely from environment variables,
    so Duo's IdP metadata never has to be hand-edited into a JSON file."""

    sp_cert = _read_file(os.environ.get("SP_CERT_FILE", ""))
    sp_key = _read_file(os.environ.get("SP_KEY_FILE", ""))

    idp_cert = os.environ.get("IDP_X509_CERT", "").strip()
    if not idp_cert:
        idp_cert = _read_file(os.environ.get("IDP_CERT_FILE", ""))

    authn_requests_signed = bool(sp_cert and sp_key)

    return {
        "strict": True,
        "debug": os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        "sp": {
            "entityId": os.environ["SP_ENTITY_ID"],
            "assertionConsumerService": {
                "url": os.environ["SP_ACS_URL"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": os.environ["SP_SLS_URL"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": sp_cert,
            "privateKey": sp_key,
        },
        "idp": {
            "entityId": os.environ.get("IDP_ENTITY_ID", ""),
            "singleSignOnService": {
                "url": os.environ.get("IDP_SSO_URL", ""),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": os.environ.get("IDP_SLS_URL", ""),
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
