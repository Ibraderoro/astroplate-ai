"""
IBM Granite multi-tier sky explanation service.

Reads WATSONX_* env vars (already loaded by main.py via load_dotenv).
Exposes a top-level `explain(plate_data, satellites) -> dict` function
that returns {"kid": str, "adult": str, "astrophysicist": str}.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

_TIERS = ("kid", "adult", "astrophysicist")


def _identify_target(ra: float, dec: float) -> str:
    """Identify prominent deep-sky catalog targets based on center coordinates."""
    if 80.0 <= ra <= 88.0 and -10.0 <= dec <= 0.0:
        return "the Orion Nebula (Messier 42) star-forming region in the constellation Orion"
    if 54.0 <= ra <= 59.0 and 22.0 <= dec <= 26.0:
        return "the Pleiades Open Star Cluster (Messier 45 / Seven Sisters) in Taurus"
    if 9.0 <= ra <= 13.0 and 39.0 <= dec <= 43.0:
        return "the Andromeda Galaxy (Messier 31), a barred spiral galaxy ~2.5 million light-years away"
    return f"a deep-sky field centered in celestial coordinates (RA {ra:.2f}°, Dec {dec:.2f}°)"


class GraniteExplainer:
    def __init__(self) -> None:
        self.api_key = os.environ.get("WATSONX_API_KEY")
        self.project_id = os.environ.get("WATSONX_PROJECT_ID")
        self.url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_id = os.environ.get("WATSONX_MODEL_ID", "ibm/granite-13b-chat-v2")

        self.client = None
        self.model = None

        if self.api_key and self.project_id:
            try:
                from ibm_watsonx_ai import APIClient, Credentials
                from ibm_watsonx_ai.foundation_models import ModelInference

                credentials = Credentials(url=self.url, api_key=self.api_key)
                self.client = APIClient(credentials=credentials, project_id=self.project_id)
                self.model = ModelInference(model_id=self.model_id, api_client=self.client)
            except Exception as e:
                print(f"[GraniteExplainer Init Error] {e}")

    # ------------------------------------------------------------------
    # Dynamic Context Builder
    # ------------------------------------------------------------------

    def _build_context(self, plate_data: dict, satellites: list) -> str:
        center_ra = float(plate_data.get("center_ra", 0.0))
        center_dec = float(plate_data.get("center_dec", 0.0))
        scale = float(plate_data.get("scale", 0.0))
        width = plate_data.get("width", 800)
        height = plate_data.get("height", 600)
        star_count = len(plate_data.get("stars", []))
        target_name = _identify_target(center_ra, center_dec)

        lines = [
            f"Target astronomical region: {target_name}.",
            f"Sky field coordinates: RA={center_ra:.4f}°, Dec={center_dec:.4f}°.",
            f"Plate scale: {scale:.3f} arcsec/pixel. Dimensions: {width}x{height} pixels.",
            f"Cataloged stars identified: {star_count}.",
        ]

        if satellites:
            sat_summaries = ", ".join(
                f"{s['name']} (NORAD ID {s['norad_id']}, Altitude: {float(s['altitude_km']):.0f} km)"
                for s in satellites
            )
            lines.append(f"Satellite passes detected intersecting the frame: {sat_summaries}.")
        else:
            lines.append("No active satellites or orbital debris passes detected in this frame.")

        return " ".join(lines)

    # ------------------------------------------------------------------
    # Dynamic Context-Aware Fallback (Zero-Downtime Demo Mode)
    # ------------------------------------------------------------------

    def _generate_dynamic_fallback(self, plate_data: dict, satellites: list) -> dict[str, str]:
        center_ra = float(plate_data.get("center_ra", 0.0))
        center_dec = float(plate_data.get("center_dec", 0.0))
        scale = float(plate_data.get("scale", 1.0))
        star_count = len(plate_data.get("stars", []))
        target_name = _identify_target(center_ra, center_dec)

        sat_streak_kid = (
            f" And look at that bright line zooming across—that's the {satellites[0]['name']} flying in orbit!"
            if satellites
            else " The sky is clear of any satellites tonight!"
        )
        sat_streak_adult = (
            f" A streak across the exposure marks an orbital pass from {satellites[0]['name']} at ~{float(satellites[0]['altitude_km']):.0f} km altitude."
            if satellites
            else " No satellite streaks interfere with this optical exposure."
        )
        sat_streak_astro = (
            f" Satellite trajectory ephemeris confirmed for {satellites[0]['name']} (NORAD {satellites[0]['norad_id']}, z ≈ {float(satellites[0]['altitude_km']):.1f} km)."
            if satellites
            else " SGP4 propagation confirms zero satellite crossing intersections across this epoch."
        )

        return {
            "kid": f"Look at {target_name}! There are {star_count} super bright stars shining in this telescope picture.{sat_streak_kid}",
            "adult": f"This observation captures {target_name}, resolving {star_count} cataloged stars at Right Ascension {center_ra:.3f}° and Declination {center_dec:.3f}°.{sat_streak_adult}",
            "astrophysicist": f"WCS astrometric calibration centers on {target_name} (α = {center_ra:.4f}°, δ = {center_dec:.4f}°) with resolution {scale:.3f}″/px. {star_count} astrometric reference stars matched.{sat_streak_astro}",
        }

    # ------------------------------------------------------------------
    # Per-tier Prompt Templates
    # ------------------------------------------------------------------

    def _tier_prompt(self, tier: str, context: str) -> str:
        instructions = {
            "kid": (
                "You are an enthusiastic astronomy guide for kids. "
                "In 2 simple, exciting sentences, explain what celestial object and stars are in this picture:"
            ),
            "adult": (
                "You are a science communicator. "
                "In 2-3 engaging, informative sentences, explain what celestial object was observed, its coordinates, and any satellite passes:"
            ),
            "astrophysicist": (
                "You are a research astrophysicist writing an observational field note. "
                "In 3 concise technical sentences, report the plate-solved target, coordinates, scale, cataloged stars, and orbital crossings:"
            ),
        }
        return f"{instructions[tier]}\n\nObservation Data:\n{context}\n\nExplanation:"

    # ------------------------------------------------------------------
    # Public Interface
    # ------------------------------------------------------------------

    def explain(self, plate_data: dict, satellites: list) -> dict[str, str]:
        if not self.model:
            return self._generate_dynamic_fallback(plate_data, satellites)

        context = self._build_context(plate_data, satellites)
        result: dict[str, str] = {}
        for tier in _TIERS:
            try:
                prompt = self._tier_prompt(tier, context)
                generated = self.model.generate_text(prompt=prompt)
                result[tier] = generated.strip()
            except Exception as e:
                print(f"[Granite Generation Error for {tier}] {e}")
                return self._generate_dynamic_fallback(plate_data, satellites)
        return result


def explain(plate_data: dict, satellites: list) -> dict[str, str]:
    """Instantiate GraniteExplainer and generate multi-tier explanation."""
    return GraniteExplainer().explain(plate_data, satellites)