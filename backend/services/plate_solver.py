"""
Astrometry.net plate-solving service.

Exposes a single synchronous entry-point:
    solve(image_bytes: bytes) -> dict
"""

from __future__ import annotations

import io
import json
import os
import time
from typing import Any

from PIL import Image
import requests

BASE_URL = "http://nova.astrometry.net"
_POLL_INTERVAL = 3.0  # seconds between status checks
_MAX_SUBMISSION_CHECKS = 30  # ~90s max to acquire job_id
_MAX_JOB_CHECKS = 40         # ~120s max to solve


class AstrometryClient:
    """Thin synchronous wrapper around the Astrometry.net HTTP API."""

    def __init__(self) -> None:
        api_key = os.environ.get("ASTROMETRY_API_KEY")
        if not api_key:
            raise RuntimeError("ASTROMETRY_API_KEY environment variable is not set.")
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self) -> str:
        """POST /api/login → session token."""
        url = f"{BASE_URL}/api/login"
        payload = {"apikey": self._api_key}
        resp = requests.post(
            url,
            data={"request-json": json.dumps(payload)},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Astrometry.net login failed: {data.get('message')}")
        session = data.get("session")
        if not session:
            raise RuntimeError(f"Astrometry.net login returned no session token: {data}")
        return session

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload(self, session: str, image_bytes: bytes) -> int:
        """Multipart POST /api/upload → submission id (int)."""
        url = f"{BASE_URL}/api/upload"
        request_json = json.dumps(
            {
                "session": session,
                "publicly_visible": "n",
                "allow_modifications": "n",
                "allow_commercial_use": "n",
            }
        )
        resp = requests.post(
            url,
            data={"request-json": request_json},
            files={"file": ("sky_frame.jpg", image_bytes, "application/octet-stream")},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Astrometry.net upload failed: {data}")
        subid = data.get("subid")
        if subid is None:
            raise RuntimeError(f"Astrometry.net upload returned no subid: {data}")
        return int(subid)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def poll_submission(self, subid: int) -> int:
        """Poll /api/submissions/{subid} until a job_id is allocated."""
        url = f"{BASE_URL}/api/submissions/{subid}"
        for _ in range(_MAX_SUBMISSION_CHECKS):
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", [])
            if jobs and jobs[0] is not None:
                return int(jobs[0])
            time.sleep(_POLL_INTERVAL)
        raise TimeoutError(f"Timed out waiting for job allocation on submission {subid}.")

    def poll_job(self, job_id: int) -> None:
        """Poll /api/jobs/{job_id} until status == 'success'."""
        url = f"{BASE_URL}/api/jobs/{job_id}"
        for _ in range(_MAX_JOB_CHECKS):
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "success":
                return
            if status == "failure":
                raise RuntimeError(f"Astrometry.net failed to plate-solve job {job_id}.")
            time.sleep(_POLL_INTERVAL)
        raise TimeoutError(f"Plate-solving timed out for job {job_id}.")

    # ------------------------------------------------------------------
    # Annotations & Calibration
    # ------------------------------------------------------------------

    def fetch_annotations(self, job_id: int) -> list[dict]:
        """Fetch identified star and deep sky object pixel locations."""
        url = f"{BASE_URL}/api/jobs/{job_id}/annotations/"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        stars: list[dict] = []
        for ann in data.get("annotations", []):
            stars.append(
                {
                    "name": ann.get("names", ["Field Star"])[0],
                    "x": float(ann.get("pixelx", 0.0)),
                    "y": float(ann.get("pixely", 0.0)),
                    "width": float(ann.get("radius", 12.0) * 2),
                    "height": float(ann.get("radius", 12.0) * 2),
                    "ra": float(ann.get("ra", 0.0)),
                    "dec": float(ann.get("dec", 0.0)),
                }
            )
        return stars

    def fetch_calibration(self, job_id: int) -> dict:
        """Fetch WCS calibration center coordinates and pixel scale."""
        url = f"{BASE_URL}/api/jobs/{job_id}/calibration/"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if not data or "ra" not in data:
            raise RuntimeError(f"Astrometry.net job {job_id} missing calibration payload: {data}")

        return {
            "center_ra": float(data["ra"]),
            "center_dec": float(data["dec"]),
            "scale": float(data["pixscale"]),
        }


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def solve(image_bytes: bytes) -> dict:
    """Synchronously solves an astronomical image via Astrometry.net."""
    # Extract dimensions reliably from source bytes
    with Image.open(io.BytesIO(image_bytes)) as img:
        width, height = img.size

    client = AstrometryClient()
    session = client.login()
    subid = client.upload(session, image_bytes)
    job_id = client.poll_submission(subid)
    client.poll_job(job_id)

    stars = client.fetch_annotations(job_id)
    calib = client.fetch_calibration(job_id)

    return {
        "width": width,
        "height": height,
        "center_ra": calib["center_ra"],
        "center_dec": calib["center_dec"],
        "scale": calib["scale"],
        "stars": stars,
    }