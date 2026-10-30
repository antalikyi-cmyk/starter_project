---
mode: agent
---

Use the official Etsy Dev MCP server to answer the user’s Etsy API question using the methods available through the Etsy MCP tools.

Follow this workflow:
1. Start with the Etsy API overview using `learn_etsy_api`.
2. Search for the relevant endpoints and schemas.
3. Inspect the exact endpoint contract and required OAuth scopes.
4. Validate the data model and auth requirements with official Etsy guidance.
5. Then answer the question with practical implementation guidance.

Important constraints:
- Do not invent Etsy endpoints or fields.
- Do not suggest protected shop actions without verifying the relevant OAuth scopes.
- Distinguish app key auth from user token auth.
- If live shop data is requested, ask whether a valid Etsy OAuth token is available.

Example tasks:
- Find endpoints for listing management and transactions.
- Explain the OAuth steps for an Etsy seller application.
- Show me the schema for `ShopReceipt` or `ShopListing`.
- Design a simple app that lists active Etsy products.
- Help sync Etsy orders into a spreadsheet or dashboard.
