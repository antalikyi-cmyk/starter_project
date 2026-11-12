# Managing Your Etsy Store with the Etsy MCP

This guide shows how to use the Etsy Dev MCP server together with an AI assistant (Claude Code, GitHub Copilot, Cursor, etc.) to manage your Etsy shop: listings, inventory, prices, orders and shipping.

> **Important: what the Etsy MCP does and does not do**
>
> The official Etsy Dev MCP server (`https://mcp.api.etsycloud.com/mcp`) is a **knowledge server**. Its tools (`learn_etsy_api`, `search_etsy_api`, `list_endpoints`, `get_endpoint`, `get_schema`, `list_guides`, `get_guide`) return documentation for Etsy Open API v3. They are read-only and **do not touch your shop**.
>
> To actually change your store, the assistant has to call the **Etsy Open API v3** (`https://api.etsy.com/v3/...`) with your app key and a seller OAuth token. The MCP tells the assistant *how* to make the call correctly. The call itself runs as a script or `curl` command from your machine.

```
 You ──prompt──► AI assistant ──"which endpoint? which scope?"──► Etsy Dev MCP (docs)
                     │
                     └──HTTP request + OAuth token──► Etsy Open API v3 ──► Your shop
```

---

## 1. One-time setup

### 1.1 Connect the Etsy MCP to your assistant

**Claude Code** (from the project root):

```bash
claude mcp add --transport http --scope project etsy https://mcp.api.etsycloud.com/mcp
```

This adds an `etsy` entry to `.mcp.json`. Restart Claude Code and run `/mcp` to check that `etsy` shows as connected.

**VS Code (Copilot)**: add the following to `.vscode/mcp.json`:

```json
{
  "servers": {
    "etsy": { "type": "http", "url": "https://mcp.api.etsycloud.com/mcp" }
  }
}
```

**Cursor / Windsurf / other clients**: add the following to the client's MCP config:

```json
{
  "mcpServers": {
    "etsy": { "type": "http", "url": "https://mcp.api.etsycloud.com/mcp" }
  }
}
```

To check the connection, ask: *"Call `learn_etsy_api` and summarize the Etsy API in 5 bullets."*

### 1.2 Register an Etsy app

1. Go to <https://www.etsy.com/developers/your-apps> and create an app.
2. Copy the **Keystring** and the **Shared secret**.
3. Add a **Callback URL** (redirect URI). For local use, `http://localhost:3003/oauth/callback` works fine. The URL does not need a running server: you only need to copy the `code` value from the browser address bar.
4. A new app starts with personal access, which is enough to manage **your own** shop.

### 1.3 Create your `.env`

```bash
cp .env.example .env
```

Fill it in:

```env
ETSY_KEYSTRING=xxxxxxxxxxxxxxxxxxxxxxxx
ETSY_SHARED_SECRET=xxxxxxxxxx
ETSY_REDIRECT_URI=http://localhost:3003/oauth/callback
ETSY_SCOPES=shops_r listings_r listings_w transactions_r transactions_w
ETSY_ACCESS_TOKEN=
ETSY_REFRESH_TOKEN=
ETSY_SHOP_ID=
```

`.env` is git-ignored. **Never commit it, and never paste tokens into a chat.** Have the assistant read them from the environment instead.

#### Choosing scopes

Request only the scopes you need:

| You want to… | Scopes |
|---|---|
| View shop info | `shops_r` |
| Change shop settings, sections, shipping profiles | `shops_w` |
| View listings | `listings_r` |
| Create or edit listings, prices, inventory, images | `listings_w` |
| Delete listings | `listings_d` |
| View orders (receipts / transactions) | `transactions_r` |
| Mark orders shipped, add tracking | `transactions_w` |
| Buyer addresses / email | `address_r`, `email_r` |

> Ask the assistant to confirm the scopes: *"Use `get_endpoint` for updateListing and tell me the required scope."* Scope names and requirements can change, and the MCP is the source of truth.

### 1.4 Get an OAuth token (PKCE)

Etsy uses OAuth 2.0 with PKCE (S256). Run these steps once. After that, refresh the token when it expires.

**Step 1: Generate a PKCE verifier and challenge** (macOS/Linux):

```bash
set -a; source .env; set +a
VERIFIER=$(openssl rand -base64 64 | tr -d '=+/\n' | cut -c1-64)
CHALLENGE=$(printf %s "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=\n')
STATE=$(openssl rand -hex 16)
echo "Keep this verifier: $VERIFIER"
```

**Step 2: Open the consent URL** and approve access:

```bash
SCOPE_ENC=$(printf %s "$ETSY_SCOPES" | sed 's/ /%20/g')
open "https://www.etsy.com/oauth/connect?response_type=code&client_id=$ETSY_KEYSTRING&redirect_uri=$ETSY_REDIRECT_URI&scope=$SCOPE_ENC&state=$STATE&code_challenge=$CHALLENGE&code_challenge_method=S256"
```

Etsy then redirects to `ETSY_REDIRECT_URI?code=...&state=...`. Check that `state` matches the value you generated, then copy `code`.

**Step 3: Exchange the code for tokens:**

```bash
curl -s -X POST https://api.etsy.com/v3/public/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d grant_type=authorization_code \
  -d client_id="$ETSY_KEYSTRING" \
  -d redirect_uri="$ETSY_REDIRECT_URI" \
  -d code="PASTE_CODE_HERE" \
  -d code_verifier="$VERIFIER"
```

Copy `access_token` and `refresh_token` from the response into `.env`. The number before the dot in the access token is your Etsy user ID.

**Step 4: Refresh when the token expires.** Access tokens last about 1 hour. Refresh tokens last about 90 days.

```bash
curl -s -X POST https://api.etsy.com/v3/public/oauth/token \
  -d grant_type=refresh_token \
  -d client_id="$ETSY_KEYSTRING" \
  -d refresh_token="$ETSY_REFRESH_TOKEN"
```

### 1.5 Find your shop ID and verify access

```bash
set -a; source .env; set +a
curl -s https://api.etsy.com/v3/application/users/me \
  -H "x-api-key: $ETSY_KEYSTRING:$ETSY_SHARED_SECRET" \
  -H "Authorization: Bearer $ETSY_ACCESS_TOKEN"
```

The response includes `shop_id`. Put it in `.env` as `ETSY_SHOP_ID`.

You can also use the bundled PowerShell checker. On macOS, install it with `brew install powershell`. It needs PowerShell 7+. The checker loads `.env` from the repo root, and values already set in your shell take precedence. If you don't have an access token yet, it prints an authorization URL with a real PKCE challenge, plus the matching `code_verifier`:

```bash
pwsh ./scripts/test-etsy-auth.ps1
```

Exit codes: `0` = OK, `1` = app credentials missing, `2` = no access token, `3` = API call failed.

---

## 2. Every request needs two headers

| Header | Value |
|---|---|
| `x-api-key` | `KEYSTRING:SHARED_SECRET` |
| `Authorization` | `Bearer ACCESS_TOKEN` (required for any shop or private endpoint) |

Write requests (`POST`/`PUT`/`PATCH`) usually take `application/x-www-form-urlencoded` or JSON bodies, depending on the endpoint. Let the assistant check this with `get_endpoint`.

---

## 3. Managing your store: example prompts

These prompts work with the agent in `.github/agents/etsy.agent.md` (also available in Claude Code as the `etsy` subagent). A good request names **what** you want and **which items**, and asks to **preview before applying**.

### Listings

| Task | Example prompt |
|---|---|
| See what's live | *"List my 25 most recent active listings with title, price, quantity and listing_id."* |
| Edit a listing | *"Change the title of listing 1234567890 to 'Handmade Oak Cutting Board'. Show me the request first."* |
| Bulk price change | *"Raise prices on all active listings tagged 'ceramics' by 10%, rounded to .99. Dry-run first and show a before/after table."* |
| Create a draft | *"Create a draft listing for a linen tote bag, $34, quantity 10, using my default shipping profile. Check required fields with `get_endpoint createDraftListing` first."* |
| Deactivate | *"Deactivate listings that have had quantity 0 for a while. List them and wait for my confirmation."* |

### Inventory and variations

| Task | Example prompt |
|---|---|
| Stock check | *"Show variations with quantity under 3 across my shop."* |
| Restock | *"Set quantity to 20 for size M of listing 1234567890 without touching other variations."* |

> The inventory endpoint replaces **all** products and offerings in one call. Ask the assistant to read the current inventory first and send back the full structure with only your change applied.

### Orders and fulfillment

| Task | Example prompt |
|---|---|
| Open orders | *"Show unshipped orders from the last 7 days: buyer name, items, ship-by date."* |
| Add tracking | *"Mark receipt 987654321 as shipped with USPS tracking 9400…, and notify the buyer."* |
| Export | *"Write a script that exports last month's receipts to `orders.csv` (date, receipt_id, total, items)."* |

### Shop and shipping

| Task | Example prompt |
|---|---|
| Shipping profiles | *"List my shipping profiles and which listings use each one."* |
| Shop sections | *"Create a shop section called 'Holiday 2026' and move listings X, Y, Z into it."* |
| Reviews | *"Summarize my last 50 reviews: average rating, common complaints."* |

### Automations

- *"Build a Node script that runs daily, finds listings with quantity below 2, and prints a restock report."*
- *"Set up token refresh so my scripts never fail on expired tokens."*
- *"Design a webhook-based flow that notifies me in Slack when a new order comes in. Check `list_guides` for webhook support first."*

---

## 4. Recommended working pattern

1. **Ask:** describe the change in plain language.
2. **Verify:** the assistant looks up the endpoint, its scopes and its schema through the MCP.
3. **Read:** it fetches the current state from your shop (GET).
4. **Preview:** it shows the exact requests and a before/after diff.
5. **Confirm:** you approve.
6. **Apply:** it runs the write requests, and for bulk changes it starts with a small batch.
7. **Check:** it re-reads the items to confirm the change.

Never skip step 5 for `PATCH`, `PUT`, `POST` or `DELETE` requests on live listings or orders. Etsy has no undo.

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `etsy` MCP not listed / tools missing | Server not configured or client not restarted | Re-run section 1.1, restart, check `/mcp` |
| `401 Unauthorized` | Access token expired (about 1 h) | Refresh the token (1.4, step 4) |
| `403` / "insufficient scope" | Token was issued without the needed scope | Add the scope to `ETSY_SCOPES` and re-run the OAuth flow |
| `x-api-key` rejected | Header missing the shared secret | Use `KEYSTRING:SHARED_SECRET` |
| `invalid_grant` on token exchange | Code reused or expired, wrong verifier, or redirect URI mismatch | Start the OAuth flow again; make sure the redirect URI matches the app settings exactly |
| `429 Too Many Requests` | Rate limit hit | Slow down, batch requests, retry with backoff (ask `learn_etsy_api` for current limits) |
| Inventory update wipes variations | Partial inventory payload sent | Always send the full products array |

---

## 6. Files in this repo

| File | Purpose |
|---|---|
| `.github/agents/etsy.agent.md` | Etsy agent instructions (single source of truth) |
| `.claude/agents/etsy.md` | Claude Code subagent wrapper that loads the file above |
| `.github/agents/etsy-store.agent.md`, `.claude/agents/etsy-store.md` | Store operator agent that changes your shop. See [ETSY-STORE-AGENT.md](ETSY-STORE-AGENT.md) |
| `scripts/etsy_api.py` | CLI for the Open API (login, auto-refresh, requests with dry run) |
| `.mcp.json` | Project MCP config (includes the `etsy` server) |
| `.github/skills/etsy-mcp/SKILL.md`, `.github/prompts/etsy-mcp.prompt.md`, `.github/commands/etsy-mcp.md` | Thin Copilot entry points that defer to the agent file |
| `.env.example` | Template for credentials and tokens |
| `scripts/test-etsy-auth.ps1` | Checks credentials and runs a test read of listings and orders |
