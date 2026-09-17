# saml-app-duo

A SAML 2.0 Service Provider with a small web UI, built to point Duo's
**Generic Service Provider** application at and test SSO end to end.

- `/` and `/profile` — the login/profile pages an end user sees.
- `/admin` — a password-protected page for entering the Duo IdP connection
  details (entity ID, SSO/SLO URLs, certificate) through a form instead of
  hand-editing files. Settings save to `instance/saml_settings.json` and
  apply immediately, no restart needed.

## 1. Install

Needs `libxml2` and `xmlsec1` dev headers for `python3-saml`'s XML signing
(prebuilt wheels usually cover this, but if `pip install` fails to build
`xmlsec`, install these first):

```bash
sudo apt-get install -y libxml2-dev libxmlsec1-dev pkg-config   # Debian/Ubuntu
# or: brew install libxml2 libxmlsec1                            # macOS

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `ADMIN_PASSWORD` (and `FLASK_SECRET_KEY`) to something
real — `ADMIN_PASSWORD` is what unlocks `/admin`.

Run it:

```bash
flask --app app run --port 5000
# or: python app.py
```

## 2. Set up the Duo side

1. In the Duo Admin Panel: **Applications > Protect an Application**, search
   for **Generic Service Provider** and click **Protect**.
2. Duo shows you IdP values — you'll paste these into this app's `/admin`
   page in the next step:
   - **Entity ID**
   - **Single Sign-On URL**
   - **Single Logout URL** (if shown)
   - **Certificate** (download it, or copy its contents)
3. Leave the Duo application's own **Service provider** fields open for now.

## 3. Configure this app via `/admin`

Go to `http://localhost:5000/admin`, log in with `ADMIN_PASSWORD`, and fill
in the **Identity provider (Duo)** fields from step 2. The certificate box
accepts the value with or without `-----BEGIN CERTIFICATE-----` lines.

The **Service provider** fields are pre-filled for local use
(`http://localhost:5000/...`) — adjust them if you're running on a different
host. Click **Save settings**.

## 4. Finish the Duo side with this app's metadata

The admin page shows this app's metadata URL
(`http://localhost:5000/saml/metadata`). Use it to fill in Duo's **Service
Provider** section for the application:

- **Entity ID** ← this app's SP entity ID
- **Assertion Consumer Service (ACS) URL** ← this app's ACS URL
- **Single Logout URL** ← this app's SLS URL (if Duo's app supports SLO)

Some Duo application types let you upload the metadata XML directly instead
of copy-pasting fields — either works.

Under the application's **Attributes** / **Permitted attributes** section,
enable at least a NameID/username claim so the app has something to display
after login.

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
  you want it (this part stays file-based, not in `/admin`).
- `instance/saml_settings.json` holds the live Duo config (including the IdP
  certificate) — it's gitignored; don't commit it.
- Session storage here is Flask's signed cookie session, fine for a demo;
  swap in server-side sessions for anything real. Likewise, `/admin` uses a
  single shared password in a cookie session — fine for a demo, not for
  production multi-admin use.
