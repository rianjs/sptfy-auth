#!/usr/bin/env python3
"""Spotify OAuth2 PKCE auth helper. Stdlib only — no pip dependencies."""

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request
import webbrowser

CONFIG_DIR = os.path.expanduser("~/.config/sptfy")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
TOKEN_PATH = os.path.join(CONFIG_DIR, "token.json")

REDIRECT_URI = "http://localhost:8765/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)


def _read_json(path):
    with open(path) as f:
        return json.load(f)


def _write_json(path, data):
    _ensure_config_dir()
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(data, f, indent=2)


def _generate_pkce():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _token_request(params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _refresh_token(config, token_data):
    resp = _token_request({
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": config["client_id"],
    })
    token_data["access_token"] = resp["access_token"]
    token_data["expires_at"] = time.time() + resp.get("expires_in", 3600)
    if "refresh_token" in resp:
        token_data["refresh_token"] = resp["refresh_token"]
    _write_json(TOKEN_PATH, token_data)
    return token_data


def cmd_login(args):
    client_id = args.client_id
    if not client_id:
        try:
            config = _read_json(CONFIG_PATH)
            client_id = config.get("client_id")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    if not client_id:
        print("Error: --client-id is required for first login", file=sys.stderr)
        sys.exit(1)

    _write_json(CONFIG_PATH, {"client_id": client_id, "redirect_uri": REDIRECT_URI})

    verifier, challenge = _generate_pkce()
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    })
    auth_url = f"{AUTH_URL}?{params}"

    authorization_code = None

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal authorization_code
            qs = urllib.parse.urlparse(self.path).query
            parsed = urllib.parse.parse_qs(qs)
            if "error" in parsed:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Error: {parsed['error'][0]}".encode())
                return
            authorization_code = parsed.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authenticated! You can close this tab.</h2>")

        def log_message(self, format, *args):
            pass  # suppress request logging

    print(f"Opening browser for Spotify authorization...")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", 8765), CallbackHandler)
    server.timeout = 120
    server.handle_request()
    server.server_close()

    if not authorization_code:
        print("Error: no authorization code received", file=sys.stderr)
        sys.exit(1)

    resp = _token_request({
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": verifier,
    })

    token_data = {
        "access_token": resp["access_token"],
        "refresh_token": resp["refresh_token"],
        "expires_at": time.time() + resp.get("expires_in", 3600),
    }
    _write_json(TOKEN_PATH, token_data)
    print("Login successful. Token saved.")


def cmd_token(_args):
    try:
        config = _read_json(CONFIG_PATH)
        token_data = _read_json(TOKEN_PATH)
    except FileNotFoundError:
        print("Error: not logged in. Run: spotify_auth.py login --client-id <ID>", file=sys.stderr)
        sys.exit(1)

    if time.time() >= token_data.get("expires_at", 0) - 60:
        token_data = _refresh_token(config, token_data)

    print(token_data["access_token"])


def cmd_status(_args):
    try:
        _read_json(CONFIG_PATH)
    except FileNotFoundError:
        print("not configured")
        return

    try:
        token_data = _read_json(TOKEN_PATH)
    except FileNotFoundError:
        print("configured but not logged in")
        return

    expires_at = token_data.get("expires_at", 0)
    if time.time() >= expires_at:
        print("authenticated (token expired, will refresh on next use)")
    else:
        remaining = int(expires_at - time.time())
        print(f"authenticated (token valid for {remaining}s)")


def main():
    parser = argparse.ArgumentParser(description="Spotify OAuth2 PKCE auth helper")
    sub = parser.add_subparsers(dest="command", required=True)

    login_p = sub.add_parser("login", help="Authenticate with Spotify")
    login_p.add_argument("--client-id", help="Spotify app client ID")

    sub.add_parser("token", help="Print valid access token to stdout")
    sub.add_parser("status", help="Show auth status")

    args = parser.parse_args()
    {"login": cmd_login, "token": cmd_token, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    main()
