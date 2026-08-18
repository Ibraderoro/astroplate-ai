# AstroPlate AI — Scaffold Plan

## Top-Level Overview

Scaffold a production-ready monorepo called **AstroPlate AI** — an autonomous astronomical plate-solving, satellite-streak detection, and multi-tier insight synthesis application. The repository splits into two independent runtimes:

- **`/backend`** — Python FastAPI service that receives an image upload, runs the full pipeline (Astrometry.net plate-solve → CelesTrak TLE satellite-tracking → IBM Granite multi-tier explanation) and returns a single consolidated JSON response.
- **`/frontend`** — Next.js 14 (App Router) with Tailwind CSS that presents an image dropzone, an HTML5 canvas overlay for star boxes and satellite trails, and a tabbed explanation card with Kid / Adult / Astrophysicist tiers.

All code is boilerplate + wiring — no real API keys or production secrets are committed.

---

## Sub-Tasks

---

### Sub-Task 1 — Backend skeleton and configuration

**Intent**
Establish the FastAPI entry-point, CORS configuration, environment variable loading, the Pydantic schema layer, and all empty `__init__.py` files so the package structure is importable before any service logic is added.

**Expected Outcomes**
- `backend/main.py` runs with `uvicorn backend.main:app` and returns `{"status":"ok"}` from `GET /health`.
- `backend/requirements.txt` lists all required packages at pinned-or-unpinned versions.
- `backend/.env.example` documents every required env var.
- `backend/models/schemas.py` defines typed Pydantic models for the request and the unified response.

**Todo List**
1. Create `backend/` directory tree: `services/`, `models/`, both `__init__.py` files.
2. Write `backend/requirements.txt` with: `fastapi`, `uvicorn[standard]`, `python-multipart`, `requests`, `ibm-watsonx-ai`, `pydantic`, `python-dotenv`, `sgp4`.
3. Write `backend/.env.example` with keys: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`, `WATSONX_MODEL_ID`, `ASTROMETRY_API_KEY`.
4. Write `backend/models/schemas.py`:
   - `AnalyzeRequest` — multipart file handle (handled by FastAPI `UploadFile`, not Pydantic), so schemas covers response side.
   - `StarAnnotation` — `x`, `y`, `width`, `height`, `ra`, `dec`.
   - `SatellitePass` — `name`, `norad_id`, `start_pixel`, `end_pixel` (list of 2 floats each), `altitude_km`.
   - `ExplanationTiers` — `kid`, `adult`, `astrophysicist` (all `str`).
   - `AnalyzeResponse` — `image_width`, `image_height`, `stars: list[StarAnnotation]`, `satellites: list[SatellitePass]`, `explanations: ExplanationTiers`, `plate_center_ra`, `plate_center_dec`, `plate_scale_arcsec_per_pixel`.
5. Write `backend/main.py`: load `.env`, create `FastAPI` app, add `CORSMiddleware` allowing all origins (dev-mode), wire `GET /health` and the stub `POST /analyze` endpoint that calls a `run_pipeline()` function (to be filled in Sub-Task 4).

**Relevant Context**
- All env vars loaded via `python-dotenv` `load_dotenv()` at module top.
- `POST /analyze` accepts `file: UploadFile` via `Form(...)` — standard FastAPI multipart pattern.

**Status:** [x] done

---

### Sub-Task 2 — `plate_solver.py` — Astrometry.net async polling orchestrator

**Intent**
Implement the full Astrometry.net submission flow: upload image bytes → poll submission status → poll job status → fetch annotations and WCS result. Return structured data matching `StarAnnotation` schema.

**Expected Outcomes**
- `backend/services/plate_solver.py` exposes a single async-compatible function `solve(image_bytes: bytes) -> dict` that returns `{ "width", "height", "center_ra", "center_dec", "scale", "stars": [...] }`.
- All HTTP calls use `requests` (sync) wrapped appropriately — the service itself is synchronous; FastAPI will call it inside `run_in_executor`.
- Polling uses exponential back-off with a configurable max-retry count.

**Todo List**
1. Write `AstrometryClient` class that reads `ASTROMETRY_API_KEY` from env on `__init__`.
2. Implement `login()` → returns session key.
3. Implement `upload(session, image_bytes)` → returns `subid`.
4. Implement `poll_submission(subid)` → polls `/api/submissions/{subid}` until `jobs` list is non-empty; returns `job_id`.
5. Implement `poll_job(job_id)` → polls `/api/jobs/{job_id}` until `status == "success"`; returns job info dict.
6. Implement `fetch_annotations(job_id)` → calls `/api/jobs/{job_id}/annotations/` → returns list of star pixel annotations.
7. Implement `fetch_wcs_info(job_id)` → calls `/api/jobs/{job_id}/info/` → extracts `ra`, `dec`, `pixscale` from `calibration` key.
8. Compose `solve(image_bytes)` top-level function that orchestrates steps 2–7 and maps results to the schema dict shape.

**Relevant Context**
- Base URL: `http://nova.astrometry.net`
- All endpoints return JSON; auth token passed as `session` field in POST bodies.
- `sgp4` is NOT used in this service; it is used in Sub-Task 3.

**Status:** [x] done

---

### Sub-Task 3 — `satellite_tracker.py` — CelesTrak TLE orbit intersection

**Intent**
Given an image capture time (UTC) and the plate-solved WCS bounding box (RA/Dec corners + pixel extent), fetch active satellite TLEs from CelesTrak, propagate orbits with `sgp4`, and identify satellites whose ground-track passes through the field of view within a configurable time window. Return pixel-space trail start/end coordinates by projecting RA/Dec back through the WCS.

**Expected Outcomes**
- `backend/services/satellite_tracker.py` exposes `find_satellites(wcs_info: dict, capture_time_utc: datetime) -> list[dict]` matching `SatellitePass` schema shape.
- CelesTrak active TLE feed fetched fresh on each call (no caching in v1).
- `sgp4` library used for orbit propagation.

**Todo List**
1. Write `fetch_tle_catalog()` → HTTP GET `https://celestrak.org/SOCRATES/query.php` or the active-sats JSON/TLE endpoint (`https://celestrak.org/SOCRATES/...`). Prefer the simpler `/pub/TLE/catalog.txt` TLE3 feed.
2. Parse raw TLE3 text into a list of `(name, line1, line2)` tuples.
3. Write `propagate(tle_tuple, t_utc)` using `sgp4` `Satrec.twoline2rv` + `sgp4` to get TEME position vector.
4. Write `teme_to_radec(pos_teme, t_utc)` — convert TEME Cartesian to RA/Dec using standard rotation (simple equatorial approximation is acceptable for v1).
5. Write `radec_in_fov(ra, dec, wcs_info)` — bounding-box test using plate center + half-width in degrees.
6. Write `radec_to_pixel(ra, dec, wcs_info)` — linear approximation using `plate_scale_arcsec_per_pixel` and center pixel.
7. Compose `find_satellites()` — iterate catalog, propagate each satellite at `capture_time_utc`, test FOV membership, build trail by propagating ±30 s, project both endpoints to pixel space.

**Relevant Context**
- `wcs_info` dict keys match what `plate_solver.solve()` returns: `center_ra`, `center_dec`, `scale` (arcsec/px), `width`, `height`.
- Use `sgp4.api.Satrec` from the `sgp4` Python package (version ≥ 2.x API).
- A satellite is included if its position at `capture_time_utc` falls within the FOV bounding box.

**Status:** [x] done

---

### Sub-Task 4 — `granite_explainer.py` — IBM Granite multi-tier synthesis

**Intent**
Call IBM Granite via `ibm-watsonx-ai` SDK to generate three explanation tiers (Kid, Adult, Astrophysicist) from a structured prompt that includes the plate-solve summary and satellite findings. Model ID and WatsonX credentials are all read from env.

**Expected Outcomes**
- `backend/services/granite_explainer.py` exposes `explain(plate_data: dict, satellites: list) -> ExplanationTiers-shaped dict`.
- Uses `ibm_watsonx_ai.foundation_models.ModelInference` (or equivalent current SDK class) with `generate_text()`.
- Three separate inference calls, one per tier, with tier-appropriate system prompt framing.

**Todo List**
1. Write `GraniteExplainer` class; `__init__` reads `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`, `WATSONX_MODEL_ID` from env and initialises `ModelInference`.
2. Write `_build_context(plate_data, satellites)` → formats a concise plain-text summary of the sky-field findings.
3. Write `_tier_prompt(tier: str, context: str)` → returns a tier-specific instruction string:
   - `"kid"` — simple language, wonder-focused, max 3 sentences.
   - `"adult"` — factual, accessible science, 2–3 sentences.
   - `"astrophysicist"` — technical, include RA/Dec, plate scale, satellite NORAD IDs, 3–5 sentences.
4. Write `explain(plate_data, satellites)` → calls `_tier_prompt` for each tier, runs `generate_text()`, returns `{"kid": ..., "adult": ..., "astrophysicist": ...}`.

**Relevant Context**
- `ibm-watsonx-ai` SDK: `from ibm_watsonx_ai import APIClient, Credentials` then `ModelInference(model_id=..., credentials=..., project_id=...)`.
- Prompt format: plain text string passed as `prompt` argument to `generate_text(prompt=...)`.

**Status:** [x] done

---

### Sub-Task 5 — Backend pipeline wiring (`main.py` `run_pipeline`)

**Intent**
Connect the three services into the `POST /analyze` endpoint's pipeline function. Read the uploaded file bytes, call `plate_solver.solve()`, pass WCS data to `satellite_tracker.find_satellites()`, pass both results to `granite_explainer.explain()`, and return a fully-populated `AnalyzeResponse`.

**Expected Outcomes**
- `POST /analyze` accepts a multipart image upload, runs the pipeline end-to-end, and returns JSON matching `AnalyzeResponse`.
- Services called synchronously inside `asyncio.get_event_loop().run_in_executor(None, ...)` so the FastAPI event loop is not blocked.
- Errors from any service are caught and surfaced as `HTTPException(500, detail=...)`.

**Todo List**
1. Import all three service modules and `AnalyzeResponse` in `main.py`.
2. Implement `run_pipeline(image_bytes, capture_time_utc)` as a regular sync function.
3. In `POST /analyze` endpoint, read `await file.read()`, derive `capture_time_utc` from an optional form field (default to `datetime.utcnow()`), then call `run_pipeline` via executor.
4. Map service return dicts → Pydantic response models and return `AnalyzeResponse`.

**Relevant Context**
- `capture_time` optional form field: ISO 8601 string, parsed with `datetime.fromisoformat()`.
- `run_in_executor` pattern: `loop = asyncio.get_event_loop(); result = await loop.run_in_executor(None, run_pipeline, image_bytes, t)`.

**Status:** [x] done

---

### Sub-Task 6 — Frontend scaffolding (Next.js 14, Tailwind, config files)

**Intent**
Initialise the `/frontend` package with all config files: `package.json`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `next.config.ts`, and the root layout + global CSS. No component logic yet — just the skeleton that compiles cleanly.

**Expected Outcomes**
- `frontend/package.json` lists Next.js 14, React 18, Tailwind CSS, Lucide React, TypeScript, and type packages.
- `frontend/app/layout.tsx` renders the Inter font, dark background, and a top navbar with the AstroPlate AI brand.
- `frontend/app/globals.css` imports Tailwind directives.
- `frontend/app/page.tsx` renders a placeholder `<main>` with a heading.
- `frontend/public/presets/` directory contains a `.gitkeep` so the folder is tracked.

**Todo List**
1. Write `frontend/package.json` with scripts (`dev`, `build`, `start`, `lint`) and all dependencies.
2. Write `frontend/tsconfig.json` (standard Next.js 14 config with path alias `@/*`).
3. Write `frontend/next.config.ts` (minimal — `images.remotePatterns` empty for now).
4. Write `frontend/tailwind.config.ts` (content paths covering `app/**` and `components/**`).
5. Write `frontend/postcss.config.js`.
6. Write `frontend/app/globals.css` with Tailwind base/components/utilities directives.
7. Write `frontend/app/layout.tsx` — root layout with Inter font, dark body, and brand navbar.
8. Write `frontend/app/page.tsx` — placeholder page.
9. Create `frontend/public/presets/.gitkeep`.

**Relevant Context**
- Use `app/` directory — App Router only (no `pages/`).
- Tailwind dark-mode strategy: `class` (controlled by a future theme toggle, not required now).

**Status:** [x] done

---

### Sub-Task 7 — `ImageDropzone.tsx` component

**Intent**
Build the image upload component that supports drag-and-drop file upload and a preset NASA image gallery. Selecting either triggers the `POST /analyze` API call and passes results up to parent state.

**Expected Outcomes**
- `frontend/components/ImageDropzone.tsx` accepts `onResult(data: AnalyzeResponse): void` and `onLoading(b: boolean): void` props.
- Drag-and-drop zone shows upload icon and hint text; highlights on dragover.
- Preset grid shows thumbnail cards sourced from `/presets/*.jpg` filenames passed as a static list.
- On file selection or preset click, posts `FormData` to `POST http://localhost:8000/analyze` and calls `onResult`.

**Todo List**
1. Define `AnalyzeResponse` TypeScript interface in `frontend/types/api.ts` mirroring the Pydantic schema.
2. Write `ImageDropzone` with local state: `dragging`, `loading`.
3. Implement drag events: `onDragOver`, `onDragLeave`, `onDrop`.
4. Implement `handleFile(file: File)` — builds `FormData`, calls `fetch`, awaits JSON, calls `onResult`.
5. Implement preset selector: static array of `{ label, filename }` objects; clicking one fetches the file from `/presets/{filename}` as a `Blob`, then calls `handleFile`.
6. Render drag-drop zone + preset grid side-by-side with Tailwind layout.

**Relevant Context**
- Preset filenames: `orion_nebula.jpg`, `andromeda.jpg`, `pleiades.jpg` — just the static list; actual images committed separately by the user.
- API base URL: read from `process.env.NEXT_PUBLIC_API_URL` with fallback `http://localhost:8000`.

**Status:** [x] done

---

### Sub-Task 8 — `SkyCanvas.tsx` component

**Intent**
Render the uploaded image on an HTML5 canvas and overlay star bounding boxes (yellow rectangles) and satellite trails (red lines with labels). Pixel coordinates come directly from the backend response.

**Expected Outcomes**
- `frontend/components/SkyCanvas.tsx` accepts `imageSrc: string`, `stars: StarAnnotation[]`, `satellites: SatellitePass[]` props.
- Canvas redraws on every prop change via `useEffect`.
- Star boxes drawn as semi-transparent yellow strokes with RA/Dec label on hover (stored in state, rendered as HTML tooltip overlay).
- Satellite trails drawn as red lines with satellite name label at midpoint.

**Todo List**
1. Write `SkyCanvas` with a `canvasRef` and a hidden `<img>` ref used to establish canvas dimensions.
2. `useEffect` on `[imageSrc, stars, satellites]` — draw image first, then overlay shapes.
3. Star rendering: `ctx.strokeStyle = "yellow"`, `ctx.strokeRect(x, y, w, h)` for each star.
4. Satellite rendering: `ctx.strokeStyle = "red"`, `ctx.beginPath()`, `moveTo` / `lineTo` between start_pixel and end_pixel, then `fillText(name)` at midpoint.
5. Hover detection: `onMouseMove` on canvas, check if pointer is inside any star rect, set `hoveredStar` state, render a positioned `<div>` tooltip with RA/Dec.

**Relevant Context**
- `StarAnnotation`: `{ x, y, width, height, ra, dec }`.
- `SatellitePass`: `{ name, norad_id, start_pixel: [x,y], end_pixel: [x,y], altitude_km }`.
- Canvas should size to image's natural dimensions, scrollable inside a fixed-height container.

**Status:** [x] done

---

### Sub-Task 9 — `ExplanationCard.tsx` component

**Intent**
Display the three Granite-generated explanation tiers in a tabbed card UI. Each tab shows one tier's text with appropriate iconography and typography.

**Expected Outcomes**
- `frontend/components/ExplanationCard.tsx` accepts `explanations: { kid: string; adult: string; astrophysicist: string }` prop.
- Three tabs: "Kid 🚀", "Adult 🔭", "Astrophysicist ⚛" — active tab highlighted.
- Explanation text rendered in a scrollable prose area.
- Lucide React icons used in tab labels (`Rocket`, `Telescope`, `Atom`).

**Todo List**
1. Write `ExplanationCard` with local `activeTab` state defaulting to `"kid"`.
2. Render tab bar with three buttons; apply active styles via Tailwind conditional classes.
3. Render active tier's text in a `<p>` inside a scrollable `<div>`.
4. Add Lucide icons alongside tab labels (`Rocket` for kid, `Telescope` for adult, `Atom` for astrophysicist).

**Relevant Context**
- Lucide React import pattern: `import { Rocket } from "lucide-react"`.
- Tailwind prose: use `text-sm leading-relaxed` for readability.

**Status:** [x] done

---

### Sub-Task 10 — Main dashboard (`app/page.tsx`) — composition

**Intent**
Wire all three components into the main page. Manage shared state (result data, loading, image preview URL) and lay out the three panels: dropzone on the left, canvas in the center, explanation card on the right.

**Expected Outcomes**
- `frontend/app/page.tsx` composes `ImageDropzone`, `SkyCanvas`, and `ExplanationCard`.
- `useState<AnalyzeResponse | null>` holds the pipeline result.
- Image preview URL derived from the uploaded file via `URL.createObjectURL`.
- Loading spinner shown while the API call is in flight.
- Three-column grid layout on large screens, stacked on mobile.

**Todo List**
1. Import all three components and the `AnalyzeResponse` type.
2. Declare state: `result`, `loading`, `imageSrc`.
3. Pass `onResult` and `onLoading` to `ImageDropzone`; on result, also derive and store `imageSrc`.
4. Conditionally render `SkyCanvas` and `ExplanationCard` only when `result !== null`.
5. Render a centered spinner (Lucide `Loader2` with `animate-spin`) when `loading === true`.
6. Apply three-column responsive grid with Tailwind (`grid-cols-1 lg:grid-cols-3 gap-6`).

**Relevant Context**
- `imageSrc` must be set before `result` so canvas has the image ready.
- `ExplanationCard` receives `result.explanations`; `SkyCanvas` receives `result.stars` and `result.satellites`.

**Status:** [x] done

---

## Implementation Notes

- Sub-Tasks 1–5 are backend-only and can be implemented in sequence.
- Sub-Tasks 6–10 are frontend-only and can be implemented in sequence after Sub-Task 6 completes.
- Backend and frontend sub-tasks are independent of each other and can be developed in parallel after Sub-Tasks 1 and 6 are complete.
- No real API credentials are committed at any point; `.env.example` is the only env file tracked.
