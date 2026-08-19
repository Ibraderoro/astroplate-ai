# Fix Plan: CelesTrak 403 & watsonx.ai Deprecated API

## Overview

Two runtime warnings are produced on every `/analyze` request:

1. **CelesTrak 403** — `fetch_tle_catalog()` in `satellite_tracker.py` receives a `403 Forbidden`
   from the primary TLE endpoint. The fallback to embedded TLEs works, but live orbital data is
   never loaded.
2. **watsonx.ai deprecated API** — `GraniteExplainer.explain()` in `granite_explainer.py` calls
   `model.generate_text()`, which the `ibm-watsonx-ai` SDK internally routes to the deprecated
   `/ml/v1/text/generation` endpoint. IBM will remove this endpoint.

Both fixes are isolated to their respective service files and have no schema or API contract changes.

---

## Sub-Task 1 — Switch CelesTrak to JSON endpoint with CDN fallback

**Intent**
Replace the single TLE URL with a two-URL cascade:
1. Primary: `https://celestrak.org/NORAD/elements/GP.php?GROUP=active&FORMAT=json` — returns a
   JSON array of satellite objects; CelesTrak does not block automated JSON clients.
2. Secondary: `https://celestrak.org/pub/TLE/catalog.txt` — raw TLE text from their CDN, less
   likely to be blocked than the `gp.php` script endpoint.
3. Tertiary (existing): embedded `FALLBACK_TLE_DATA` constant.

The disk cache must still work — cache the raw response text/JSON as-is, and detect which format
is stored when reading it back.

**Expected Outcomes**
- No `403` warning in logs during normal operation.
- Live TLE data loads from the JSON endpoint.
- If the JSON endpoint also fails, the CDN text URL is tried before the embedded fallback.
- Cache TTL behavior (24 hours) is unchanged.

**Todo List**
1. Add a new constant `CELESTRAK_JSON_URL` and `CELESTRAK_CDN_TLE_URL` alongside the existing
   `CELESTRAK_TLE_URL` constant (keep old constant for reference/fallback label only).
2. Add a helper `_parse_json_catalog(text: str)` that parses the JSON array from CelesTrak and
   returns `List[Tuple[str, str, str]]` — each item a `(name, line1, line2)` tuple. The JSON
   schema CelesTrak returns includes `OBJECT_NAME`, `TLE_LINE1`, `TLE_LINE2` keys.
3. Rewrite `fetch_tle_catalog()` to:
   - Check disk cache first (unchanged).
   - Try `CELESTRAK_JSON_URL` — if successful, store raw JSON text to cache, parse with
     `_parse_json_catalog()`, and return.
   - If JSON URL fails (any exception/non-200), try `CELESTRAK_CDN_TLE_URL` — if successful,
     store raw TLE text to cache, parse with existing `_parse_tle_lines()`, and return.
   - If both fail, fall back to stale cache then embedded TLEs (unchanged logic).
4. Update cache read logic: detect whether the cached file content starts with `[` (JSON array)
   or is TLE text, and dispatch to the correct parser.

**Relevant Context**
- File: `backend/services/satellite_tracker.py`
- Constants block: lines 24–28
- `fetch_tle_catalog()`: lines 50–86
- `_parse_tle_lines()`: lines 89–106 (reused as-is)

**Status**: [x] done

---

## Sub-Task 2 — Migrate GraniteExplainer from `generate_text` to the chat API

**Intent**
Replace the call to `model.generate_text(prompt=prompt)` with the newer
`model.chat(messages=[...])` interface. This routes requests through `/ml/v1/text/chat`,
eliminating the `WatsonxAPIWarning` and future-proofing against endpoint removal.

The prompt content and structure stays identical — only the call signature changes. The model
initialization (`ModelInference`) stays the same; only the invocation method changes.

**Expected Outcomes**
- No `WatsonxAPIWarning` in logs.
- `explain()` still returns the same `dict[str, str]` with `kid`, `adult`, `astrophysicist` keys.
- Fallback behavior on parse failure is unchanged.

**Todo List**
1. In `GraniteExplainer.explain()`, replace:
   ```python
   generated = self.model.generate_text(prompt=prompt)
   ```
   with:
   ```python
   response = self.model.chat(messages=[{"role": "user", "content": prompt}])
   generated = response["choices"][0]["message"]["content"]
   ```
2. Keep the existing `_extract_json_block()` parsing and fallback logic entirely unchanged.
3. Remove the now-unused `GenParams` import if it is no longer needed after migration
   (check whether `params` dict keys can stay as plain strings or still need `GenParams`
   constants — if `GenParams` is only used for the `params` dict at init, it stays).

**Relevant Context**
- File: `backend/services/granite_explainer.py`
- `GraniteExplainer.__init__()`: lines 48–78 — `ModelInference` init with `params` stays
- `GraniteExplainer.explain()`: lines 148–163 — only line 156 changes
- IBM SDK docs: `ModelInference.chat(messages)` returns a dict with
  `choices[0].message.content`

**Status**: [x] done
