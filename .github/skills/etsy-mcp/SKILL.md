---
name: etsy-mcp
description: Use Etsy Open API v3 via the official Etsy Dev MCP server for API discovery, schema lookup, OAuth guidance, and shop integration planning.
---

# Etsy MCP Skill

## Purpose
Use this skill whenever the task involves Etsy API integration, app setup, OAuth flows, listing management, order handling, or documentation lookup.

## Required MCP server
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

## Workflow
1. Start with `learn_etsy_api` to understand scope and authentication.
2. Search for relevant endpoints using `search_etsy_api`.
3. Use `list_endpoints` to browse the relevant groups.
4. Use `get_endpoint` to inspect parameters, schema, and required scopes.
5. Use `get_schema` for complex models like `ShopReceipt`, `ShopListing`, or `Money`.
6. Use `list_guides` and `get_guide` for auth, webhooks, and rate limits.
7. Only after verifying the official spec, generate code, flow diagrams, or integration guidance.

## Rules
- Do not invent endpoints or fields.
- Verify OAuth scopes and auth requirements before suggesting protected requests.
- Distinguish between app-level API key auth and user OAuth token auth.
- For shop orders and listing details, require a valid user access token.
- Use official Etsy docs as the primary source of truth.

## Typical tasks
- find listing endpoints and required scopes
- explain how to request an Etsy OAuth token
- inspect schemas for shop and receipt models
- design a workflow for syncing listings or orders
- assess which Etsy endpoints fit a user’s integration need

## Response style
- concise and structured
- focus on the exact API contract and required permissions
- provide examples for OAuth and request headers when relevant
- mention when a live action requires user authorization and a valid access token
