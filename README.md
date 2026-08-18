# AstroPlate AI 🌌🔭

> **Astrometric plate-solving, orbital satellite trail identification, and multi-tier astrophysical reasoning powered by IBM Granite.**

---

## 🌟 Overview

**AstroPlate AI** is a full-stack astronomical analysis platform designed to turn raw astrophotography frames into rich, contextual celestial data. When an astronomical frame is uploaded:

1. **Astrometric Plate-Solving:** The backend queries Astrometry.net (or falls back to preset catalog matching) to calculate the celestial World Coordinate System (WCS), determining right ascension (RA), declination (Dec), orientation, and arcsec/pixel scale.
2. **Orbital Satellite Tracking:** Using SGP4 orbital propagation and live CelesTrak two-line element (TLE) datasets, the system calculates whether known satellites (e.g., ISS, Starlink) crossed the telescope's field of view (FOV) at the time of capture, rendering their trajectory streaks.
3. **IBM Granite Astrophysical Synthesis:** The telemetry, plate scale, star counts, and satellite crossing data are sent to an **IBM Granite** foundation model via **IBM watsonx.ai** to generate three distinct explanation tiers:
* 🚀 **Kid:** Wonder-filled, easy-to-understand explanations for younger audiences.
* 🔭 **Adult / Enthusiast:** Clear, engaging science communication covering constellations and satellites.
* ⚛ **Astrophysicist:** Rigorous observational field notes with technical WCS and orbital parameters.


4. **Interactive Sky Canvas:** The frontend renders bounding boxes on identified stars, hover tooltips for RA/Dec coordinate inspection, and offers one-click exports for annotated `.png` images and raw `.json` telemetry.

---

## 🛠️ Tech Stack

### **Backend**

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
* **Plate-Solving:** [Astrometry.net API](https://nova.astrometry.net/) & NASA SkyView Digitized Sky Survey (DSS)
* **Orbital Mechanics:** [SGP4](https://pypi.org/project/sgp4/) & [Skyfield](https://rhodesmill.org/skyfield/) with CelesTrak TLE feeds
* **AI & LLM:** [IBM watsonx.ai](https://www.ibm.com/products/watsonx-ai) (`ibm/granite-13b-chat-v2` / `ibm-granite`)
* **Image Processing:** [Pillow (PIL)](https://pillow.readthedocs.io/)
* **Streaming Protocol:** Server-Sent Events (SSE) via `StreamingResponse`

### **Frontend**

* **Framework:** [Next.js 14](https://nextjs.org/) (App Router, React, TypeScript)
* **Styling:** [Tailwind CSS](https://tailwindcss.com/)
* **Icons:** [Lucide React](https://lucide.dev/)
* **Canvas & Graphics:** Responsive SVG & HTML5 Canvas overlays with interactive mouse tracking

---

## 🤖 Built With Bob (IBM AI Assistant)

This project was scaffolded end-to-end using **[Bob](https://www.ibm.com/products/bob)**, IBM's AI coding assistant. Bob authored the [`astroplate-ai-plan.md`](astroplate-ai-plan.md) planning document, which decomposed the project into 10 sequential sub-tasks covering the full monorepo. Working through each sub-task in agent mode, Bob generated the complete FastAPI backend skeleton and Pydantic schemas, the Astrometry.net plate-solving service, the SGP4/CelesTrak orbital satellite tracker, and the IBM Granite multi-tier explanation service — including the context-aware `_generate_dynamic_fallback` in `granite_explainer.py` for zero-downtime demo operation. On the frontend, Bob scaffolded all five Next.js components (`ImageDropzone`, `SkyCanvas`, `ExplanationCard`, `AnalysisProgress`, and the main `page.tsx` dashboard), the SSE streaming pipeline in `main.py`, and the Docker Compose configuration for single-command full-stack deployment. Bob also assisted with iterative debugging throughout development, helping resolve integration issues across the backend pipeline and frontend component wiring.

---

## 📁 Project Structure

```text
astroplate-ai/
├── backend/
│   ├── main.py                     # FastAPI application & SSE pipeline streamer
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Backend container configuration
│   ├── .env.example                # Template for environment variables
│   ├── models/
│   │   └── schemas.py              # Pydantic data schemas
│   └── services/
│       ├── plate_solver.py         # Astrometry.net API client
│       ├── satellite_tracker.py    # SGP4 orbital propagator
│       └── granite_explainer.py    # IBM watsonx / Granite integration
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # Global layout & metadata
│   │   └── page.tsx                # Main sky analyzer page
│   ├── components/
│   │   ├── AnalysisProgress.tsx    # Live multi-stage pipeline stepper
│   │   ├── ExplanationCard.tsx     # Multi-tier explanation tabs (Kid/Adult/Astro)
│   │   ├── ImageDropzone.tsx       # Drag-and-drop uploader & preset selector
│   │   └── SkyCanvas.tsx           # Interactive canvas with SVG overlays & export
│   ├── public/
│   │   └── presets/                # NASA SkyView test frames (Orion, Andromeda, Pleiades)
│   ├── types/
│   │   └── api.ts                  # TypeScript interfaces for backend responses
│   ├── Dockerfile                  # Multi-stage Next.js production build
│   └── package.json
│
├── docker-compose.yml              # Single-command full-stack containerization
└── README.md

```

---

## 🚀 Quick Start (Docker Compose)

The fastest way to launch the entire stack (FastAPI backend + Next.js frontend):

### 1. Clone the repository

```bash
git clone https://github.com/your-username/astroplate-ai.git
cd astroplate-ai

```

### 2. Configure Environment Variables

Create a `backend/.env` file:

```bash
cp backend/.env.example backend/.env

```

Fill in your credentials:

```ini
ASTROMETRY_API_KEY=your_astrometry_api_key
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-chat-v2

```

### 3. Launch Containers

```bash
docker compose up --build

```

* **Frontend Application:** [http://localhost:3000](http://localhost:3000)
* **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Backend Healthcheck:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 💻 Manual Local Development

If you prefer running services directly on your host machine:

### Backend Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start the FastAPI development server
PYTHONPATH=. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

```

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install npm dependencies
npm install

# 3. Start Next.js in development mode
npm run dev

```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📡 API Reference

### `POST /analyze`

Accepts a multipart form upload of an astronomical frame and streams real-time Server-Sent Events (SSE) detailing each pipeline stage.

* **Form Data:**
* `file`: Binary image file (`image/jpeg` or `image/png`).
* `capture_time` *(optional)*: ISO-8601 capture timestamp (defaults to current UTC).


* **SSE Stream Events:**
* `event: progress` — Emits status payloads `{ "step": "upload" | "astrometry" | "satellites" | "granite", "message": "..." }`.
* `event: complete` — Emits the final `AnalyzeResponse` payload:



```json
{
  "image_width": 800,
  "image_height": 800,
  "plate_center_ra": 56.7502,
  "plate_center_dec": 24.1098,
  "plate_scale_arcsec_per_pixel": 1.02,
  "stars": [
    { "x": 190.0, "y": 180.0, "width": 36.0, "height": 36.0, "ra": 56.55, "dec": 24.05 }
  ],
  "satellites": [
    {
      "name": "STARLINK-3142",
      "norad_id": 48123,
      "start_pixel": [80.0, 720.0],
      "end_pixel": [740.0, 180.0],
      "altitude_km": 550.2
    }
  ],
  "explanations": {
    "kid": "Look at the Pleiades Open Star Cluster!...",
    "adult": "This observation captures the Pleiades cluster...",
    "astrophysicist": "WCS astrometric calibration centers on the Pleiades (α = 56.7502°, δ = 24.1098°)..."
  }
}

```

---

## 📸 Key Features & UI Controls

* **Preset Gallery:** Preloaded with genuine Digitized Sky Survey (DSS) optical star fields for the **Orion Nebula (M42)**, **Andromeda Galaxy (M31)**, and **Pleiades Cluster (M45)**.
* **Coordinate Hover Tooltip:** Move your cursor over any yellow detection box to inspect the star's calculated RA/Dec coordinates.
* **Export PNG:** Generates a merged, high-resolution snapshot containing the source sky frame, star boxes, and satellite tracks.
* **Export JSON:** Downloads the full telemetry payload (WCS center coordinates, plate scale, star listings, and ephemerides).
* **Fault-Tolerant Resilience:** Includes automatic fallback generators for zero-downtime offline demos and portfolio presentations.

---

## 🛰️ Technical Approximations & Known Limitations

To maintain sub-second response times across cloud environments without requiring mandatory client GPS permissions, the current pipeline employs standard architectural simplifications:

1. **Geocentric Orbital Coordinates:** Satellite RA/Dec ephemerides are computed directly from Earth-Centered TEME vectors (`teme_to_radec()`). Because topocentric parallax adjustments (observer latitude, longitude, and elevation) are omitted in this baseline, apparent positions for Low Earth Orbit (LEO, 400–550 km) objects serve as an astrometric proximity approximation rather than precise topocentric sightlines.
2. **Illumination & Twilight Constraints:** The orbital model checks spatial intersection across the celestial field of view without computing instantaneous solar phase angles, Earth shadow penumbra entry, or local solar depression angle (twilight visibility).
3. **Graceful Pipeline Degradation:** In offline environments or upon external API rate limits/timeouts, the engine automatically flags data provenance with a `"source": "fallback"` tag and surfaces a clear UI banner detailing the simulated fallback match.

---

## 📜 Acknowledgements & Data Attribution

* **Astronomical Imagery:** Preset optical star fields for the Orion Nebula (M42), Andromeda Galaxy (M31), and Pleiades (M45) are sourced from NASA SkyView and the **Digitized Sky Survey (DSS)**, produced at the Space Telescope Science Institute (STScI) under U.S. Government grant NAG W-2166.
* **Plate-Solving Service:** Astrometric indexing and quad-tree catalog reductions powered by the [Astrometry.net](https://nova.astrometry.net/) API.
* **Orbital Ephemerides:** Two-Line Element (TLE) satellite catalog feeds provided by [CelesTrak](https://celestrak.org/).

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
