# Etsy MCP Workspace

This workspace contains a ready-to-use Etsy MCP setup for exploring Etsy Open API v3 documentation, planning integration work, and handling Etsy API-related tasks with Copilot and MCP-compatible tools.

## What is included
- Etsy-focused MCP agent instructions
- custom Copilot guidance for Etsy API work
- a starter skill and prompt for Etsy MCP usage
- environment variables for Etsy app credentials and OAuth tokens
- an auth validation script for testing Etsy access

## Etsy MCP configuration
Add the following to your MCP client configuration:

```json
{
  "mcpServers": {
    "etsy": {
      "type": "http",
      "url": "https://mcp.api.etsycloud.com/mcp"
    }
  }
}
```

## How to use the Etsy MCP agent
The agent is designed to:
- discover relevant Etsy endpoints and schemas
- explain authentication requirements and scopes
- guide OAuth 2.0 flows
- help with listings, orders, shops, shipping, reviews, and integrations
- recommend implementation patterns aligned with Etsy's official Open API v3 docs

### Example prompts
- "Use the Etsy MCP server to find the endpoints for managing listings and inventory."
- "Show me the schema for ShopReceipt and explain the required OAuth scopes."
- "How do I request an authorization code and access token for my Etsy app?"
- "Build a simple app that reads Etsy shop data and displays active listings."
- "Help me design a workflow to sync Etsy orders into my local dashboard."

## What can be done via Etsy MCP
- API discovery for Etsy Open API v3
- endpoint lookup by keyword or group
- schema inspection for models such as ShopListing, Money, ShopReceipt, and others
- guide lookup for authentication, OAuth, webhooks, and rate limits
- integration planning for shops, listings, transactions, and shipping
- code generation grounded in official Etsy docs instead of generic API guesses

## Required credentials
The workspace stores app credentials in `.env` to support local testing:

```env
ETSY_KEYSTRING=your_keystring
ETSY_SHARED_SECRET=your_shared_secret
ETSY_ACCESS_TOKEN=your_oauth_access_token
ETSY_REFRESH_TOKEN=your_oauth_refresh_token
ETSY_REDIRECT_URI=https://your-app.example.com/callback
ETSY_SCOPES=shops_r transactions_r listings_r
```

## OAuth workflow summary
Etsy requires two layers of auth:
1. API key authentication using the app keystring and shared secret for API requests.
2. User OAuth 2.0 access token for private shop data like listings, orders, receipts, and transactions.

Typical flow:
1. Request an authorization code from Etsy.
2. Exchange the code for an access token and refresh token.
3. Use the access token on protected endpoints.
4. Refresh the token as needed.

## Verification and testing
Use the PowerShell helper script to validate the current client configuration:

```powershell
pwsh ./scripts/test-etsy-auth.ps1
```

This script checks for the app key and OAuth state and tells you whether a live shop listing/order fetch is possible.

## Notes
- A valid OAuth access token is required to fetch current items and orders for a shop.
- App credentials alone are not enough for private shop endpoints.
- The official Etsy MCP server should be treated as the authoritative source for endpoint and schema questions.
