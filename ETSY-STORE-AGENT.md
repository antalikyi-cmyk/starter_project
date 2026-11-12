# Etsy Store Agent

The **etsy-store** agent runs your Etsy shop from chat. You describe what you want ("raise mug prices 10%", "add tracking to yesterday's orders"). The agent finds the right items, shows you exactly what will change, waits for your OK, then makes the change through the Etsy Open API v3.

| | `etsy` agent | `etsy-store` agent |
|---|---|---|
| Purpose | Explains the API and designs integrations | Operates your shop |
| Touches your shop | No | Yes, after you confirm |
| Instructions | `.github/agents/etsy.agent.md` | `.github/agents/etsy-store.agent.md` |

---

## Setup (once)

1. **Connect the Etsy MCP and create an Etsy app.** Follow [ETSY-MCP-USAGE.md](ETSY-MCP-USAGE.md), sections 1.1–1.2. Set the app's callback URL to `http://localhost:3003/oauth/callback`.
2. **Fill in `.env`:**
   ```env
   ETSY_KEYSTRING=...
   ETSY_SHARED_SECRET=...
   ETSY_REDIRECT_URI=http://localhost:3003/oauth/callback
   ETSY_SCOPES=shops_r shops_w listings_r listings_w transactions_r transactions_w
   ```
   Add `listings_d` if you want the agent to be able to delete listings. Add `billing_r` for payment and ledger reports.
3. **Log in.** This opens Etsy in your browser and saves the tokens and your shop ID to `.env`:
   ```bash
   python3 scripts/etsy_api.py login
   ```
4. **Check it works:**
   ```bash
   python3 scripts/etsy_api.py whoami
   ```

The token refreshes automatically. If the refresh token expires (about 90 days), run `login` again.

### Starting the agent
- **Claude Code:** ask for it by name, e.g. *"Use the etsy-store agent to show my unshipped orders"*, or pick it from `/agents`.
- **VS Code Copilot:** choose **etsy-store** in the Chat agent picker.

---

## What it can do

| Area | Abilities |
|---|---|
| **Shop** | View shop details, announcement and policies; update shop title, announcement and sale message |
| **Listings** | List by state (active, draft, inactive, expired, sold out); search your listings by title or tag; edit title, description, tags, materials, section and shipping profile; create drafts; activate or deactivate; delete (with extra confirmation) |
| **Pricing** | Set prices; bulk percentage or fixed changes with `.99` rounding; per-variation prices |
| **Inventory** | Stock reports; restock per variation or SKU; low-stock and sold-out alerts |
| **Orders** | List unpaid, unshipped or shipped orders; order details; add tracking and mark shipped; export to CSV |
| **Shop sections** | List, create and rename sections; move listings between sections |
| **Shipping** | List shipping profiles and their destinations; find listings by profile; reassign profiles |
| **Reviews** | Fetch reviews; rating summary; spot recurring complaints |
| **Finances** | Ledger entries and payouts for a date range (needs `billing_r`) |
| **Automation** | Write scheduled scripts: daily low-stock report, order export, price-sync checks |

**Not supported yet:** uploading images or videos (multipart upload; the agent can write a one-off script for it), Etsy Ads, messaging buyers (not in the public API), and anything that goes against Etsy policy.

---

## How a change works

```
You:    Raise prices on all active mugs by 10%, round to .99
Agent:  Found 8 active listings tagged "mug". Backup saved to backups/2026-11-12-mug-prices.json
        | Listing                    | Now    | New    |
        |----------------------------|--------|--------|
        | Speckled Stoneware Mug     | $28.00 | $30.99 |
        | Blue Glaze Espresso Cup    | $18.00 | $19.99 |
        | …6 more                    |        |        |
        Endpoint: PUT listings/{id}/inventory (full inventory sent; other variations unchanged)
        Apply these 8 changes?
You:    yes
Agent:  Updated 1/8 and verified, then 7 more. All 8 done. Prices re-checked.
```

The agent always does this:
1. Resolves your description into concrete items.
2. Saves a backup.
3. Shows a preview.
4. Waits for your **yes**.
5. Applies one item first, then the rest in small batches.
6. Re-checks the result.

The CLI enforces this too: write requests don't run without `--yes`.

---

## Example prompts

**Overview**
- *"Give me a shop snapshot: active listings, total stock, unshipped orders, last 30 days revenue."*
- *"Which 10 listings have the lowest stock?"*

**Listings**
- *"Show my draft listings."*
- *"Add the tag 'gift for her' to every listing in the Jewelry section that has fewer than 13 tags."*
- *"Rewrite the descriptions of my 3 oldest listings to be clearer. Show me each one before saving."*
- *"Create a draft for a linen tote bag, $34, 10 in stock, same category and shipping profile as listing 1234567890."*
- *"Deactivate everything in the 'Summer 2026' section."*

**Prices and stock**
- *"Put 15% off all listings in the Prints section, rounded to .99. I'll revert it on Monday."*
- *"Revert the price change from backup backups/2026-11-12-prints-sale.json."*
- *"Set size M of listing 1234567890 to 20 in stock and leave the other sizes alone."*
- *"List every variation that is sold out."*

**Orders**
- *"Show unshipped orders, oldest first, with the ship-by date."*
- *"Mark order 3456789012 as shipped: USPS, tracking 9400111202555842761234."*
- *"Here's a CSV of receipt_id,carrier,tracking. Add tracking to all of them."*
- *"Export October orders to exports/orders-2026-10.csv."*

**Shop organisation**
- *"Create a 'Holiday 2026' section and move listings 111, 222 and 333 into it."*
- *"Which listings still use the old 'Standard US' shipping profile?"*

**Insight**
- *"Summarize my last 100 reviews: average rating, top 3 praises, top 3 complaints."*
- *"How much did Etsy fees cost me last month?"*

**Automation**
- *"Write a script that emails me (or prints) listings with stock below 3 every morning, and tell me how to schedule it with cron."*

---

## Using the CLI directly

The agent uses `scripts/etsy_api.py`, and you can run it yourself:

```bash
# Read
python3 scripts/etsy_api.py whoami
python3 scripts/etsy_api.py request GET 'shops/{shop_id}/listings/active' -q limit=25
python3 scripts/etsy_api.py request GET 'shops/{shop_id}/receipts' -q was_shipped=false --all

# Write: preview first (prints the request and exits 4) ...
python3 scripts/etsy_api.py request PATCH 'shops/{shop_id}/listings/1234567890' -f title='Handmade Oak Cutting Board'
# ... then apply
python3 scripts/etsy_api.py request PATCH 'shops/{shop_id}/listings/1234567890' -f title='Handmade Oak Cutting Board' --yes

# JSON body from a file
python3 scripts/etsy_api.py request PUT 'listings/1234567890/inventory' --json-file inventory.json --yes
```

### Endpoint cheat sheet

Paths are relative to `https://api.etsy.com/v3/application`. The agent confirms each one with the MCP (`get_endpoint`) before first use, so treat this table as a starting point, not the final word.

| Task | Method & path | Scope |
|---|---|---|
| Me / shop ID | `GET users/me` | — |
| Shop details | `GET shops/{shop_id}` | — |
| Update shop | `PUT shops/{shop_id}` | `shops_w` |
| Listings by state | `GET shops/{shop_id}/listings?state=active\|draft\|inactive\|expired\|sold_out` | `listings_r` |
| One listing | `GET listings/{listing_id}` | — / `listings_r` for non-active |
| Create draft | `POST shops/{shop_id}/listings` | `listings_w` |
| Edit listing / change state | `PATCH shops/{shop_id}/listings/{listing_id}` | `listings_w` |
| Delete listing | `DELETE listings/{listing_id}` | `listings_d` |
| Inventory (price, qty, SKU) | `GET` / `PUT listings/{listing_id}/inventory` | `listings_r` / `listings_w` |
| Orders | `GET shops/{shop_id}/receipts` | `transactions_r` |
| One order | `GET shops/{shop_id}/receipts/{receipt_id}` | `transactions_r` |
| Add tracking | `POST shops/{shop_id}/receipts/{receipt_id}/tracking` | `transactions_w` |
| Sections | `GET` / `POST shops/{shop_id}/sections` | — / `shops_w` |
| Shipping profiles | `GET shops/{shop_id}/shipping-profiles` | `shops_r` |
| Reviews | `GET shops/{shop_id}/reviews` | — |
| Ledger | `GET shops/{shop_id}/payment-account/ledger-entries` | `billing_r` |
| Categories | `GET seller-taxonomy/nodes` | — |

---

## Safety notes

- **Secrets stay in `.env`** (git-ignored, file mode 600). The agent is told never to print them.
- **Backups** go to `backups/` and **exports** to `exports/`. Both are git-ignored because they contain shop and buyer data.
- **Costs:** activating or renewing a listing charges a listing fee. Adding tracking may email the buyer. The agent mentions both in its preview.
- **Deletion** can't be undone. The agent suggests deactivating instead.
- **Claude Code permissions:** each `etsy_api.py` call asks for approval by default. To skip prompts for reads only, allow `Bash(python3 scripts/etsy_api.py request GET:*)` and keep write calls on manual approval.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing in environment/.env: ...` | Fill in `.env`, then run `login` |
| `login` hangs | Check that the app's callback URL is exactly `ETSY_REDIRECT_URI`, and that port 3003 is free |
| `State mismatch` | Run `login` again, using only the newest browser tab |
| 403 "API key not found … shared secret" | Wrong `ETSY_KEYSTRING` or `ETSY_SHARED_SECRET` |
| 403 insufficient scope | Add the scope to `ETSY_SCOPES` and run `login` again |
| 401 after auto-refresh | Refresh token expired; run `login` |
| 429 | Too many requests; the agent slows down. Try smaller batches |
