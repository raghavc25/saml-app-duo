# saml-app-duo

A SAML 2.0 Service Provider with a small web UI, built to point Duo's
**Generic Service Provider** application at and test SSO end to end.

- `/` and `/profile` — the login/profile pages an end user sees.
- `/admin` — a password-protected page for entering the Duo IdP connection
  details (entity ID, SSO/SLO URLs, certificate) and the SSO session lifetime
  through a form instead of hand-editing files. Settings save to `instance/saml_settings.json` and
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

Edit `.env`:

- `FLASK_SECRET_KEY` — set to a real random value (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`). It signs session cookies, including the `/admin` login flag — don't leave it as the placeholder on anything network-reachable.
- `ADMIN_PASSWORD` — what unlocks `/admin`.
- `FLASK_RUN_HOST` — `127.0.0.1` for local-only access, `0.0.0.0` to accept connections from other hosts on your network.

## 2. Point a hostname at this box (optional but recommended)

If this app needs to be reachable by something other than `localhost` (e.g.
Duo redirecting a real browser back to it), give it a proper FQDN rather than
an IP:

1. Add an A record for your chosen hostname (e.g. `app.example.com`) pointing
   at this box's IP in your DNS server.
2. Update the seed `SP_ENTITY_ID` / `SP_ACS_URL` / `SP_SLS_URL` in `.env`
   (or later via `/admin`) to use that hostname instead of `localhost`.
3. Confirm it resolves from wherever you'll actually browse from — not just
   from this box, since it may use a different DNS server.

## 3. TLS (recommended for anything beyond a quick local test)

The app can serve HTTPS directly, no reverse proxy required:

1. Generate a key + CSR:
   ```bash
   cd certs
   openssl req -new -newkey rsa:2048 -nodes \
     -keyout https_key.pem -out https.csr \
     -subj "/CN=app.example.com" \
     -addext "subjectAltName=DNS:app.example.com"
   ```
2. Get `https.csr` signed by your CA. If it comes back as a PKCS#7 bundle
   (common from Microsoft AD CS — still starts with `-----BEGIN
   CERTIFICATE-----` but decodes as PKCS#7), split it into individual certs
   first: `openssl pkcs7 -in received.p7b -print_certs -out certs.pem`, then
   concatenate leaf + any intermediate/root into one file (leaf first).
3. Save that combined file as `certs/https_cert.pem`.
4. In `.env`, set:
   ```
   SP_HTTPS=on
   HTTPS_CERT_FILE=/absolute/path/to/certs/https_cert.pem
   HTTPS_KEY_FILE=/absolute/path/to/certs/https_key.pem
   ```
5. Update `SP_ENTITY_ID` / `SP_ACS_URL` / `SP_SLS_URL` to `https://...` (in
   `.env` if not yet saved via `/admin`, or directly in `/admin` otherwise).

`certs/*.key`, `*.pem`, `*.csr` and `*.cnf` are gitignored — the private key
never gets committed.

If you skip this, `SP_HTTPS` stays `off` and the app runs plain HTTP — fine
for a quick localhost test, not for anything Duo will actually redirect a
real user's browser to.

## 4. Run it persistently (systemd)

For anything longer-lived than a one-off test, run it as a service instead of
a foreground/background shell process — it'll survive logout and reboot, and
restart itself if it crashes:

```bash
sudo cp saml-duo-app.service /etc/systemd/system/saml-duo-app.service
sudo systemctl daemon-reload
sudo systemctl enable --now saml-duo-app
sudo systemctl status saml-duo-app
```

`saml-duo-app.service` assumes the app lives at `/home/cisco/saml-duo-app`
and runs as user `cisco` — edit the unit file first if either differs.

Logs: `journalctl -u saml-duo-app -f`
Restart after config changes: `sudo systemctl restart saml-duo-app`

For quick manual testing instead, you can still run it directly:

```bash
flask --app app run --port 5000
# or: python app.py
```

## 5. Set up the Duo side

1. In the Duo Admin Panel: **Applications > Protect an Application**, search
   for **Generic Service Provider** and click **Protect**.
2. Duo shows you IdP values — you'll paste these into this app's `/admin`
   page in the next step:
   - **Entity ID**
   - **Single Sign-On URL**
   - **Single Logout URL** (if shown)
   - **Certificate** (download it, or copy its contents)
3. Leave the Duo application's own **Service provider** fields open for now.

## 6. Configure this app via `/admin`

Go to `https://<your-host>:5000/admin` (or `http://` if you skipped TLS), log
in with `ADMIN_PASSWORD`, and fill in the **Identity provider (Duo)** fields
from step 5. The certificate box accepts the value with or without
`-----BEGIN CERTIFICATE-----` lines.

The **Service provider** fields are pre-filled from `.env` — adjust them if
your hostname, port, or scheme changed since.

Under **SSO session**, set **Session lifetime (minutes)** — how long a user
stays logged in after a Duo login (default 480, i.e. 8 hours; seeded from
`SESSION_LIFETIME_MINUTES` in `.env` on first run). Click **Save settings**.

### How the SSO session works

- After a successful Duo login the app sets a **persistent** session cookie
  with an expiry, so the login survives closing and reopening the browser.
- The lifetime counts from login — it isn't extended by activity. When it
  runs out, the next page load sends the user back to `/login` and through
  Duo again.
- Expiry is enforced by the server as well as the browser: a cookie older
  than the configured lifetime is rejected even if the browser still sends it.
- Changing the lifetime applies without a restart. New logins get the new
  value; shortening it also ends existing sessions early, while lengthening
  it doesn't extend sessions already in progress.
- With `SP_HTTPS=on` the cookie is marked `Secure`; it's always `HttpOnly`
  and `SameSite=Lax`.
- Duo keeps its own SSO session separately, so after the app's session
  expires the user may get back in without a fresh 2FA prompt, depending on
  your Duo policy.

## 7. Finish the Duo side with this app's metadata

The admin page shows this app's metadata URL. Use it to fill in Duo's
**Service Provider** section for the application:

- **Entity ID** ← this app's SP entity ID
- **Assertion Consumer Service (ACS) URL** ← this app's ACS URL
- **Single Logout URL** ← this app's SLS URL (if Duo's app supports SLO)

Some Duo application types let you upload the metadata XML directly instead
of copy-pasting fields — either works. **If you change the SP entity ID / ACS
URL / SLS URL later (e.g. moving from HTTP to HTTPS), you must update these
fields in Duo too** — a mismatch here is a common cause of login failures.

Under the application's **Permitted attributes** section, enable whichever
attributes you want released (username, email, groups, etc.). If none are
enabled, Duo's assertion carries only the NameID — the app handles that fine
and just shows an empty-state hint on `/profile`; it does not require an
`AttributeStatement` to be present.

Assign the Duo policy/groups you want to be able to use this app, then click
**Save**.

## 8. Test it

1. Go to your app's URL and click **Log in with Duo**.
2. You're redirected to Duo, complete primary auth + 2FA.
3. Duo POSTs a SAML Response back to `/saml/acs`; on success you land on
   `/profile` showing the NameID and any released attributes.
4. Close and reopen the browser and revisit `/profile` — you should still
   be logged in until the session lifetime set in `/admin` runs out.
5. **Log out** clears your local session immediately and also sends a
   best-effort SAML LogoutRequest to Duo — if Duo's SLO isn't configured or
   doesn't redirect back, you're still logged out of this app either way.

## Notes

- Signing AuthnRequests from the SP side is optional and off by default; run
  `./generate_sp_cert.sh` and set `SP_CERT_FILE`/`SP_KEY_FILE` in `.env` if
  you want it (this part stays file-based, not in `/admin`, and is unrelated
  to the HTTPS cert/key above).
- `instance/saml_settings.json` holds the live Duo config (including the IdP
  certificate) — it's gitignored; don't commit it.
- Session storage here is Flask's signed cookie session, fine for a demo;
  swap in server-side sessions for anything real. Likewise, `/admin` uses a
  single shared password in a cookie session — fine for a demo, not for
  production multi-admin use.
- The dev server (`flask run` / `python app.py`, including under systemd
  here) is single-threaded and not hardened for production traffic — fine
  for a lab/demo integration, swap in a real WSGI server (gunicorn, uwsgi)
  behind it for anything more serious.
