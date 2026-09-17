import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, request, redirect, session, render_template, Response, url_for
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings

load_dotenv()

from saml_config import get_saml_settings  # noqa: E402  (needs load_dotenv() first)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# Duo redirects the browser back over HTTPS in production; tell Flask to trust
# that when it builds absolute URLs for the SAML request/response.
app.config["PREFERRED_URL_SCHEME"] = "https" if os.environ.get("SP_HTTPS", "off") == "on" else "http"


def prepare_flask_request(flask_request):
    url_data = urlparse(flask_request.url)
    return {
        "https": "on" if os.environ.get("SP_HTTPS", "off") == "on" else "off",
        "http_host": flask_request.host,
        "server_port": url_data.port,
        "script_name": flask_request.path,
        "get_data": flask_request.args.copy(),
        "post_data": flask_request.form.copy(),
        "query_string": flask_request.query_string,
    }


def init_saml_auth(flask_request):
    req = prepare_flask_request(flask_request)
    return OneLogin_Saml2_Auth(req, get_saml_settings())


@app.route("/")
def index():
    return render_template("home.html", user=session.get("samlUserdata"), name_id=session.get("samlNameId"))


@app.route("/login")
def login():
    auth = init_saml_auth(request)
    return redirect(auth.login())


@app.route("/saml/acs", methods=["POST"])
def acs():
    """Assertion Consumer Service: Duo POSTs the SAML Response here after login."""
    auth = init_saml_auth(request)
    auth.process_response()
    errors = auth.get_errors()

    if errors:
        return render_template(
            "error.html",
            errors=errors,
            reason=auth.get_last_error_reason(),
        ), 400

    if not auth.is_authenticated():
        return render_template("error.html", errors=["not_authenticated"], reason="Duo did not confirm authentication"), 401

    session["samlUserdata"] = auth.get_attributes()
    session["samlNameId"] = auth.get_nameid()
    session["samlNameIdFormat"] = auth.get_nameid_format()
    session["samlSessionIndex"] = auth.get_session_index()

    relay_state = request.form.get("RelayState")
    if relay_state and relay_state != request.url_root:
        return redirect(relay_state)
    return redirect(url_for("profile"))


@app.route("/profile")
def profile():
    if "samlNameId" not in session:
        return redirect(url_for("login"))
    return render_template("profile.html", name_id=session["samlNameId"], attributes=session.get("samlUserdata") or {})


@app.route("/logout")
def logout():
    auth = init_saml_auth(request)
    name_id = session.get("samlNameId")
    session_index = session.get("samlSessionIndex")
    name_id_format = session.get("samlNameIdFormat")

    return redirect(
        auth.logout(
            name_id=name_id,
            session_index=session_index,
            nq=None,
            name_id_format=name_id_format,
        )
    )


@app.route("/saml/sls", methods=["GET", "POST"])
def sls():
    """Single Logout Service: handles both IdP-initiated logout and the
    response to an SP-initiated logout request."""
    auth = init_saml_auth(request)

    def clear_session():
        session.pop("samlUserdata", None)
        session.pop("samlNameId", None)
        session.pop("samlNameIdFormat", None)
        session.pop("samlSessionIndex", None)

    url = auth.process_slo(delete_session_cb=clear_session)
    errors = auth.get_errors()

    if errors:
        return render_template("error.html", errors=errors, reason=auth.get_last_error_reason()), 400

    return redirect(url or url_for("index"))


@app.route("/saml/metadata")
def metadata():
    """SP metadata XML — give this URL (or its downloaded XML) to Duo when
    configuring the Generic Service Provider application."""
    settings = OneLogin_Saml2_Settings(settings=get_saml_settings(), sp_validation_only=True)
    metadata_xml = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata_xml)

    if errors:
        return Response("\n".join(errors), status=500, content_type="text/plain")
    return Response(metadata_xml, content_type="text/xml")


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_RUN_PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
