#!/usr/bin/env python3
"""Minimal Etsy Open API v3 CLI used by the etsy-store agent.

Commands:
  login                      Run the OAuth 2.0 PKCE flow and save tokens + shop ID to .env
  refresh                    Refresh the access token and save it to .env
  whoami                     Show the authenticated user and shop ID
  request METHOD PATH [...]  Call any Open API v3 endpoint

PATH is relative to https://api.etsy.com/v3/application and may contain
{shop_id}, which is replaced with ETSY_SHOP_ID. Write requests (anything
other than GET) only print a preview unless --yes is passed.

Exit codes: 0 ok, 1 config error, 2 HTTP error, 4 dry run (write not sent).
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, ".env")
API_BASE = "https://api.etsy.com/v3/application"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
CONNECT_URL = "https://www.etsy.com/oauth/connect"
DEFAULT_SCOPES = "shops_r shops_w listings_r listings_w transactions_r transactions_w"


def load_env():
    """Load .env into os.environ without overriding variables already set."""
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value and not os.environ.get(key.strip()):
                os.environ[key.strip()] = value


def save_env(updates):
    """Write key=value pairs into .env, replacing existing keys."""
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            lines = f.read().splitlines()
    remaining = dict(updates)
    for i, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            lines[i] = "%s=%s" % (key, remaining.pop(key))
    lines += ["%s=%s" % (k, v) for k, v in remaining.items()]
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_FILE, 0o600)
    os.environ.update({k: str(v) for k, v in updates.items()})


def require(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        die("Missing in environment/.env: %s (see ETSY-MCP-USAGE.md)" % ", ".join(missing), 1)
    return [os.environ[n] for n in names]


def die(message, code):
    print(message, file=sys.stderr)
    sys.exit(code)


def call(method, url, headers=None, body=None):
    """Return (status, parsed_json_or_text)."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    text = raw.decode("utf-8", "replace")
    try:
        return status, json.loads(text) if text else None
    except ValueError:
        return status, text


def token_request(fields):
    body = urllib.parse.urlencode(fields).encode()
    status, data = call("POST", TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body)
    if status != 200 or not isinstance(data, dict) or "access_token" not in data:
        die("Token request failed (%s): %s" % (status, data), 2)
    save_env({"ETSY_ACCESS_TOKEN": data["access_token"], "ETSY_REFRESH_TOKEN": data["refresh_token"]})
    return data


def api_headers():
    key, secret = require("ETSY_KEYSTRING", "ETSY_SHARED_SECRET")
    headers = {"x-api-key": "%s:%s" % (key, secret), "Accept": "application/json",
               "User-Agent": "etsy-store-agent"}
    if os.environ.get("ETSY_ACCESS_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["ETSY_ACCESS_TOKEN"]
    return headers


def cmd_refresh(_args=None):
    key, refresh_token = require("ETSY_KEYSTRING", "ETSY_REFRESH_TOKEN")
    data = token_request({"grant_type": "refresh_token", "client_id": key, "refresh_token": refresh_token})
    print("Access token refreshed (expires in %ss)." % data.get("expires_in"), file=sys.stderr)


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def cmd_login(args):
    key, redirect_uri = require("ETSY_KEYSTRING", "ETSY_REDIRECT_URI")
    scopes = args.scopes or os.environ.get("ETSY_SCOPES") or DEFAULT_SCOPES
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)
    url = CONNECT_URL + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": key, "redirect_uri": redirect_uri, "scope": scopes,
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256"})

    redirect = urllib.parse.urlparse(redirect_uri)
    print("Opening Etsy consent page:\n" + url, file=sys.stderr)
    webbrowser.open(url)

    if redirect.hostname in ("localhost", "127.0.0.1"):
        result = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != redirect.path:
                    self.send_response(404)
                    self.end_headers()
                    return
                result.update(urllib.parse.parse_qs(parsed.query))
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Etsy authorization received. You can close this tab.")

            def log_message(self, *_):
                pass

        server = http.server.HTTPServer((redirect.hostname, redirect.port or 80), Handler)
        print("Waiting for redirect on %s ..." % redirect_uri, file=sys.stderr)
        while "code" not in result and "error" not in result:
            server.handle_request()
        server.server_close()
        params = {k: v[0] for k, v in result.items()}
    else:
        pasted = input("Paste the full URL Etsy redirected you to: ").strip()
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(pasted).query))

    if "error" in params:
        die("Authorization denied: %s" % params, 2)
    if params.get("state") != state:
        die("State mismatch; aborting.", 2)
    token_request({"grant_type": "authorization_code", "client_id": key, "redirect_uri": redirect_uri,
                   "code": params["code"], "code_verifier": verifier})
    save_env({"ETSY_SCOPES": scopes})
    status, me = call("GET", API_BASE + "/users/me", api_headers())
    if status == 200 and isinstance(me, dict) and me.get("shop_id"):
        save_env({"ETSY_SHOP_ID": me["shop_id"]})
    print("Logged in. Tokens%s saved to .env." % (" and shop ID" if status == 200 else ""), file=sys.stderr)


def send(method, url, body, content_type):
    headers = api_headers()
    if body is not None:
        headers["Content-Type"] = content_type
    status, data = call(method, url, headers, body)
    if status == 401 and os.environ.get("ETSY_REFRESH_TOKEN"):
        cmd_refresh()
        headers = api_headers()
        if body is not None:
            headers["Content-Type"] = content_type
        status, data = call(method, url, headers, body)
    return status, data


def cmd_request(args):
    method = args.method.upper()
    path = args.path
    if "{shop_id}" in path:
        path = path.replace("{shop_id}", require("ETSY_SHOP_ID")[0])
    query = dict(q.split("=", 1) for q in args.query)
    url = API_BASE + "/" + path.lstrip("/")

    body, content_type = None, None
    if args.json_file:
        with open(args.json_file) as f:
            args.json = f.read()
    if args.json is not None:
        body, content_type = json.dumps(json.loads(args.json)).encode(), "application/json"
    elif args.form:
        body = urllib.parse.urlencode([tuple(f.split("=", 1)) for f in args.form]).encode()
        content_type = "application/x-www-form-urlencoded"

    if method != "GET" and not args.yes:
        print(json.dumps({"dry_run": True, "method": method, "url": url,
                          "query": query, "content_type": content_type,
                          "body": body.decode() if body else None}, indent=2))
        print("Not sent. Re-run with --yes to apply.", file=sys.stderr)
        sys.exit(4)

    if method == "GET" and args.all:
        limit, offset, results, count = int(query.get("limit", 100)), int(query.get("offset", 0)), [], None
        while count is None or offset < count:
            query.update(limit=str(limit), offset=str(offset))
            status, data = send(method, url + "?" + urllib.parse.urlencode(query), None, None)
            if status >= 400:
                die(json.dumps({"status": status, "error": data}, indent=2), 2)
            results += data.get("results", [])
            count = data.get("count", 0)
            offset += limit
            if not data.get("results"):
                break
        print(json.dumps({"count": count, "results": results}, indent=2))
        return

    full_url = url + ("?" + urllib.parse.urlencode(query) if query else "")
    status, data = send(method, full_url, body, content_type)
    if status >= 400:
        die(json.dumps({"status": status, "error": data}, indent=2), 2)
    print(json.dumps(data, indent=2) if not isinstance(data, str) else data)


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="OAuth PKCE login; saves tokens and shop ID to .env")
    login.add_argument("--scopes", help="space-separated scopes (default: ETSY_SCOPES or common read/write set)")
    sub.add_parser("refresh", help="refresh the access token")
    sub.add_parser("whoami", help="GET /users/me")

    req = sub.add_parser("request", help="call an Open API v3 endpoint")
    req.add_argument("method", help="GET, POST, PUT, PATCH or DELETE")
    req.add_argument("path", help="e.g. shops/{shop_id}/listings/active")
    req.add_argument("-q", "--query", action="append", default=[], metavar="KEY=VALUE")
    req.add_argument("--json", help="JSON request body")
    req.add_argument("--json-file", help="read JSON request body from a file")
    req.add_argument("-f", "--form", action="append", default=[], metavar="KEY=VALUE",
                     help="form-encoded body field (repeatable)")
    req.add_argument("--all", action="store_true", help="GET only: follow limit/offset pagination")
    req.add_argument("--yes", action="store_true", help="actually send a write request")

    args = parser.parse_args()
    if args.command == "login":
        cmd_login(args)
    elif args.command == "refresh":
        cmd_refresh(args)
    elif args.command == "whoami":
        args.method, args.path, args.query, args.json, args.json_file = "GET", "users/me", [], None, None
        args.form, args.all, args.yes = [], False, False
        cmd_request(args)
    else:
        cmd_request(args)


if __name__ == "__main__":
    main()
