# SAML SP demo (Flask + python3-saml) — Duo integration

A minimal SAML 2.0 Service Provider you can point Duo's **Generic Service
Provider** application at, to test SSO end to end.

## 1. Install

Needs `libxml2` and `xmlsec1` dev headers for `python3-saml`'s XML signing:

```bash
sudo apt-get install -y libxml2-dev libxmlsec1-dev pkg-config   # Debian/Ubuntu
# or: brew install libxml2 libxmlsec1                            # macOS

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Set up the Duo side first

1. In the Duo Admin Panel: **Applications > Protect an Application**, search
   for **Generic Service Provider** and click **Protect**.
2. Duo shows you IdP values you'll need — copy them into `.env`:
   - **Entity ID** → `IDP_ENTITY_ID`
   - **Single Sign-On URL** → `IDP_SSO_URL`
   - **Single Logout URL** (if shown) → `IDP_SLS_URL`
   - **Certificate** → download it and point `IDP_CERT_FILE` at the file
     (or paste its base64 body into `IDP_X509_CERT`).
3. Leave the Duo application's own **Service provider** fields open for now —
   you'll fill those in from this app's metadata in the next step.

## 3. Configure this app

Edit `.env`:

- `SP_ENTITY_ID` — any unique URI; the default (`.../saml/metadata`) is fine.
- `SP_ACS_URL` — where this app receives the SAML response, e.g.
  `http://localhost:5000/saml/acs`.
- `SP_SLS_URL` — where this app receives logout messages, e.g.
  `http://localhost:5000/saml/sls`.

Run it:

```bash
flask --app app run --port 5000
# or: python app.py
```

## 4. Finish the Duo side with this app's metadata

Visit `http://localhost:5000/saml/metadata` (or `curl` it) and use the values
to fill in Duo's **Service Provider** section for the application:

- **Entity ID** ← this app's `SP_ENTITY_ID`
- **Assertion Consumer Service (ACS) URL** ← this app's `SP_ACS_URL`
- **Single Logout URL** ← this app's `SP_SLS_URL` (if Duo's app supports SLO)

Some Duo application types let you upload the metadata XML directly instead
of copy-pasting fields — either works.

Under the application's **Attributes** / **Permitted attributes** section,
enable at least a NameID/username claim so the app has something to display
after login (see `templates/profile.html`).

Assign the Duo policy/groups you want to be able to use this app, then click
**Save**.

## 5. Test it

1. Go to `http://localhost:5000/` and click **Log in with Duo**.
2. You're redirected to Duo, complete primary auth + 2FA.
3. Duo POSTs a SAML Response back to `/saml/acs`; on success you land on
   `/profile` showing the NameID and any released attributes.
4. **Log out** triggers SP-initiated SLO back through Duo.

## Notes

- `SP_HTTPS=off` is only for local testing. Set it to `on` and serve over
  real HTTPS before pointing this at anything but a Duo sandbox — Duo signs
  responses but the browser round-trip should still be TLS-protected end to
  end in production.
- Signing AuthnRequests from the SP side is optional and off by default; run
  `./generate_sp_cert.sh` and set `SP_CERT_FILE`/`SP_KEY_FILE` in `.env` if
  you want it.
- Session storage here is Flask's signed cookie session, fine for a demo;
  swap in server-side sessions for anything real.
