# Alter-ego Autopilot — Cover asset contract (slide 1)

For: GrokBot Scout. Date: 2026-10-17. Ticket: AE-0418.
Status: **NOT LIVE YET.** Do not send `cover` or call `/assets` until Pedro confirms AE-0418 is
deployed. Before that, a topic with `cover` is rejected (422, unknown key) for the whole batch.

Everything in the topics contract (`autopilot-topics-contract-pov-news.md`) stays the same. This
adds one optional upload and one optional topic field.

## 1. What it does

You can attach a cover image to a topic. Slide 1 still uses Pedro's photo (or the usual Radar IA
cover) **by default**. Pedro sees your cover on Telegram and decides per post with the
"Usar capa do Grok" button. Never assume your cover will be used.

Works for every mode: `news_analysis`, `pov` and `pov_news`.

## 2. Two kinds of cover

| kind | What it is | How it renders |
|---|---|---|
| `ai_image` | An image you generated. Nothing taken from someone else. | Full-bleed on slide 1, under the title (like Pedro's photo). Keep the top ~30% calm: the title sits there. |
| `screenshot` | A post screenshot, product shot or logo from a source of the topic. | A framed card on the dark background, title above it, small credit under it (`@handle · X` for X, otherwise the domain). |

## 3. Upload: `POST /api/autopilot/assets`

- Header `X-Api-Key`. Body `multipart/form-data` with:
  - `file` (required): exactly one PNG or JPEG, ≤ 5 MB.
  - `kind` (required): `ai_image` or `screenshot`.
  - `source_url` (required for `screenshot`): the URL the image comes from (for X, the canonical
    `https://x.com/<handle>/status/<id>` you sent to `/x-signals`).
- Response **201**:
  ```json
  { "asset_id": "3f0c…", "kind": "ai_image", "width": 1080, "height": 1350 }
  ```

Image rules (checked on the real bytes, not the declared type):

| Rule | `ai_image` | `screenshot` |
|---|---|---|
| Format | PNG or JPEG | PNG or JPEG |
| Size | ≤ 5 MB | ≤ 5 MB |
| Minimum | 1080×1350 after a centre crop to 4:5 | 600 px wide |
| Maximum | 4096 px a side, 16 MP | 4096 px a side, 16 MP |
| Crop | centre-cropped to 4:5 (send 4:5 to control the framing) | never cropped |

The backend re-encodes the file and strips metadata. An asset expires **6 hours** after upload
if no topic uses it, and each asset can be used by **one** topic.

Upload errors (4xx, body `{ "detail": "<code>" }`):

| Code | When |
|---|---|
| `asset_too_large` | file over 5 MB, or over 4096 px / 16 MP |
| `asset_too_small` | below the minimum for its kind |
| `asset_type_unsupported` | not a real PNG or JPEG |
| `asset_kind_invalid` | `kind` missing or not `ai_image` / `screenshot` |
| `asset_source_missing` | `screenshot` without `source_url` |
| 401 `invalid_api_key` / 429 | as on the other routes |

## 4. Topic field `cover`

Add to any topic:

```json
"cover": { "asset_id": "3f0c…" }
```

Per-topic rejections (that topic only, with `index` and `field: "cover.asset_id"`):

| Reason | When |
|---|---|
| `cover_asset_unknown` | no asset with that id |
| `cover_asset_expired` | uploaded more than 6 hours ago |
| `cover_asset_used` | already attached to another topic |
| `cover_source_invalid` | a `screenshot` whose `source_url` is not in this topic's `sources` |

A rejected topic is not stored; fix it and send it again (the asset stays usable until it expires).

## 5. Order of calls in one run

1. `GET /signals` and/or `POST /x-signals` (as today).
2. `POST /assets` for each cover (one call per image).
3. `POST /topics` with `cover.asset_id` on the topics that have one.

## 6. Rules for the scout

- `ai_image`: generate it for the topic; no real people other than generic figures, no logos or
  brand marks you don't have a source for, no text in the image (the title is rendered on top).
- `screenshot`: only from a post or page listed in the topic's `sources`; never edit or crop out the
  author; never use a screenshot of private content.
- One cover per topic. Don't send a cover you would not want published.
- Never publish anything; Pedro decides on Telegram.

## 7. Example

```
POST /api/autopilot/assets   (multipart: file=cover.png, kind=ai_image)
→ 201 { "asset_id": "3f0c9b1e-…", "kind": "ai_image", "width": 1080, "height": 1350 }

POST /api/autopilot/topics
{ "topics": [ { "mode": "pov_news",
                "title": "…", "angle": "…", "why_viral": "…", "audience": "devs", "niche": "agentes de IA",
                "brief": "…", "sources": ["https://x.com/poteto/status/2111133080526495985"], "score": 80,
                "thesis_draft": "…",
                "cover": { "asset_id": "3f0c9b1e-…" } } ] }
```

---

## Appendix: backend notes (not part of the Grok contract)

Added by AE-0418 on the backend side; nothing here changes the contract above.

- **HTTP status per upload code:** `asset_too_large` 413, `asset_type_unsupported` 415,
  `asset_too_small` / `asset_kind_invalid` / `asset_source_missing` 422. No owner user
  configured on the backend: 503 `autopilot_owner_unconfigured` (server-side, not Grok's fault).
- **Missing `file` part:** `asset_type_unsupported`. A `source_url` that is not an http(s) URL
  counts as missing. A `source_url` sent with an `ai_image` is ignored.
- **Size reported:** an `ai_image` is centre-cropped to 4:5 and scaled to exactly 1080×1350
  (the slide size), so its 201 body always says 1080×1350. A `screenshot` keeps its size.
- **`cover.asset_id`** that is not a UUID is `cover_asset_unknown` for that topic (not a batch
  422). Unknown keys inside `cover` are a batch 422 (like every other object).
- **Used:** an asset becomes used when a topic that names it is stored. Within one batch the
  first topic wins and a second topic with the same asset gets `cover_asset_used`.
- **Screenshot source:** compared with the topic `sources` after the same normalisation the
  sources get (an X status URL on twitter.com or x.com matches its canonical x.com form).
- **Storage:** the re-encoded WebP is a `carousel_creator_assets` row with role `cover` (never
  listed in the owner's photo library); `autopilot_cover_assets` keeps kind, source and the
  topic that used it. Unused rows older than 6 h are deleted by the Telegram notify tick.
- **Owner choice:** `ap:cv:<run>` / `ap:cvoff:<run>` on the thesis message (POV modes) and on
  every review message. See [ADR-0024](../decisions/0024-grok-cover-asset.md).
