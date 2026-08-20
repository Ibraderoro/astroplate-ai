"""
CelesTrak TLE satellite orbit tracker with local disk caching and SGP4 propagation.

Fetches active satellite orbital elements, propagates each orbit with sgp4,
and identifies satellites whose projected trajectory falls inside the plate-solved
field of view at the given capture time.
"""

from __future__ import annotations

import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Tuple

import requests
from sgp4.api import Satrec, jday

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

CELESTRAK_JSON_URL = "https://celestrak.org/NORAD/elements/GP.php?GROUP=active&FORMAT=json"
CELESTRAK_CDN_TLE_URL = "https://celestrak.org/pub/TLE/catalog.txt"
CACHE_FILE = "/tmp/celestrak_active_tles.txt"
CACHE_TTL_SECONDS = 86400  # 24 hours
EARTH_RADIUS_KM = 6378.137
FOV_MARGIN_DEG = 0.2  # Margin around plate FOV bounding box

# Circuit breaker: once CelesTrak refuses us (403/blocked), stop retrying it for a
# cooldown period instead of hammering it on every /analyze call. Per CelesTrak's own
# usage policy, repeating a request after a 403 does not help and risks a harder,
# longer-lived IP-level block.
CIRCUIT_BREAKER_FILE = "/tmp/celestrak_circuit_breaker.txt"
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 3600  # 1 hour

# Standard browser request headers to prevent WAF bot-filter blocks
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Embedded high-profile sample TLEs for zero-downtime offline demo resilience
FALLBACK_TLE_DATA = """ISS (ZARYA)
1 25544U 98067A   24080.52924769  .00014782  00000+0  26477-3 0  9993
2 25544  51.6416 290.3164 0004944 122.9525 284.8144 15.49815049444743
HST
1 20580U 90037B   24080.45678901  .00001234  00000+0  54321-4 0  9992
2 20580  28.4695 115.8234 0002847  75.1234 285.1234 15.09345678123456
STARLINK-1007
1 44713U 19074A   24080.50000000  .00001000  00000+0  10000-4 0  9991
2 44713  53.0500 120.0000 0001500  90.0000 270.0000 15.06000000200001
STARLINK-30121
1 56214U 23048A   24080.60000000  .00002000  00000+0  20000-4 0  9995
2 56214  43.0000 180.0000 0001200 100.0000 260.0000 15.12000000300002
"""


# ---------------------------------------------------------------------------
# 1. Cached TLE Catalog Fetch & Parse
# ---------------------------------------------------------------------------

def _parse_json_catalog(text: str) -> List[Tuple[str, str, str]]:
    """Parse CelesTrak JSON response into (name, line1, line2) tuples safely."""
    import json as _json
    try:
        entries = _json.loads(text)
        if not isinstance(entries, list):
            return []
        catalog: List[Tuple[str, str, str]] = []
        for entry in entries:
            name = entry.get("OBJECT_NAME", "UNKNOWN").strip()
            line1 = entry.get("TLE_LINE1", "").strip()
            line2 = entry.get("TLE_LINE2", "").strip()
            if line1.startswith("1 ") and line2.startswith("2 "):
                catalog.append((name, line1, line2))
        return catalog
    except Exception as e:
        print(f"[SatelliteTracker] JSON parse error: {e}")
        return []


def _load_cache() -> List[Tuple[str, str, str]] | None:
    """Read and parse the disk cache, auto-detecting JSON vs TLE text format."""
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return None
        if content.lstrip().startswith("["):
            return _parse_json_catalog(content)
        return _parse_tle_lines(content.splitlines())
    except Exception as e:
        print(f"[SatelliteTracker] Cache read warning: {e}")
        return None


def _circuit_breaker_tripped() -> bool:
    """True if CelesTrak recently blocked us and we should skip live calls for a while."""
    if not os.path.exists(CIRCUIT_BREAKER_FILE):
        return False
    return (time.time() - os.path.getmtime(CIRCUIT_BREAKER_FILE)) < CIRCUIT_BREAKER_COOLDOWN_SECONDS


def _trip_circuit_breaker() -> None:
    """Record that CelesTrak just returned 403, so we stop retrying for a cooldown period."""
    try:
        with open(CIRCUIT_BREAKER_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"[SatelliteTracker] Could not write circuit breaker file: {e}")


def fetch_tle_catalog() -> Tuple[List[Tuple[str, str, str]], str, str | None]:
    """
    Retrieve active satellite TLEs: disk cache → JSON API → CDN TLE text → embedded fallback.

    Returns:
        (catalog, source, reason) where source is one of
        "cache" | "live_json" | "live_cdn" | "stale_cache" | "embedded_fallback",
        and reason is a short human-readable explanation (None for the healthy "cache"/"live_*" cases).
    """
    # 1. Serve from cache if still fresh
    if os.path.exists(CACHE_FILE):
        if (time.time() - os.path.getmtime(CACHE_FILE)) < CACHE_TTL_SECONDS:
            result = _load_cache()
            if result:
                return result, "cache", None

    # 1b. If CelesTrak recently blocked us, don't hammer it again this hour —
    # go straight to stale cache / embedded fallback instead. Per CelesTrak's own
    # usage policy, repeating a request after a 403 doesn't help and risks a
    # harder, longer-lived IP-level block.
    if _circuit_breaker_tripped():
        if os.path.exists(CACHE_FILE):
            result = _load_cache()
            if result:
                return (
                    result,
                    "stale_cache",
                    "CelesTrak recently blocked this server; reusing stale cache during cooldown.",
                )
        return (
            _parse_tle_lines(FALLBACK_TLE_DATA.splitlines()),
            "embedded_fallback",
            "CelesTrak recently blocked this server; using embedded sample catalog during cooldown.",
        )

    blocked = False

    # 2. Try JSON endpoint with browser headers
    try:
        resp = requests.get(CELESTRAK_JSON_URL, headers=BROWSER_HEADERS, timeout=8)
        if resp.status_code == 403:
            blocked = True
        resp.raise_for_status()
        content = resp.text
        catalog = _parse_json_catalog(content)
        if catalog:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            return catalog, "live_json", None
    except Exception as e:
        print(f"[SatelliteTracker] JSON TLE fetch failed ({e}). Trying CDN fallback.")

    # 3. Try CDN raw TLE text
    try:
        resp = requests.get(CELESTRAK_CDN_TLE_URL, headers=BROWSER_HEADERS, timeout=8)
        if resp.status_code == 403:
            blocked = True
        resp.raise_for_status()
        content = resp.text
        catalog = _parse_tle_lines(content.splitlines())
        if catalog:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            return catalog, "live_cdn", None
    except Exception as e:
        print(f"[SatelliteTracker] CDN TLE fetch failed ({e}). Falling back to cached/embedded TLEs.")

    # Both endpoints 403'd — trip the breaker so we stop retrying for a while.
    if blocked:
        _trip_circuit_breaker()

    # 4. Stale cache, then embedded fallback
    if os.path.exists(CACHE_FILE):
        result = _load_cache()
        if result:
            return (
                result,
                "stale_cache",
                "CelesTrak unreachable; served TLEs from stale local cache.",
            )
    return (
        _parse_tle_lines(FALLBACK_TLE_DATA.splitlines()),
        "embedded_fallback",
        "CelesTrak unreachable (blocked or rate-limited); using a small embedded sample catalog (ISS, HST, 2 Starlink).",
    )


def _parse_tle_lines(raw_lines: Sequence[str]) -> List[Tuple[str, str, str]]:
    """Parse 3-line TLE format into clean tuples."""
    lines = [line.strip() for line in raw_lines if line.strip()]
    catalog: List[Tuple[str, str, str]] = []

    i = 0
    while i + 2 < len(lines):
        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if line1.startswith("1 ") and line2.startswith("2 "):
            catalog.append((name, line1, line2))
            i += 3
        else:
            i += 1

    return catalog


# ---------------------------------------------------------------------------
# 2. SGP4 Orbit Propagation
# ---------------------------------------------------------------------------

def _datetime_to_jd(t: datetime) -> Tuple[float, float]:
    """Convert UTC datetime to Julian Date pair (jd, fr) for SGP4."""
    return jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)


def propagate(
    tle_tuple: Tuple[str, str, str],
    t_utc: datetime,
) -> Tuple[float, float, float] | None:
    """Propagate TLE to t_utc. Returns TEME Cartesian position (km) or None."""
    _, line1, line2 = tle_tuple
    try:
        sat = Satrec.twoline2rv(line1, line2)
    except Exception:
        return None

    jd, fr = _datetime_to_jd(t_utc)
    err, r, _ = sat.sgp4(jd, fr)

    if err != 0:
        return None
    return (r[0], r[1], r[2])


# ---------------------------------------------------------------------------
# 3. TEME Coordinates → Celestial RA / Dec
# ---------------------------------------------------------------------------

def teme_to_radec(pos_teme: Tuple[float, float, float]) -> Tuple[float, float]:
    """
    Convert TEME Cartesian position directly to geocentric Right Ascension and Declination.
    TEME is an Earth-Centered inertial frame aligned with the celestial equator.
    """
    x, y, z = pos_teme
    r_xy = math.sqrt(x**2 + y**2)
    ra_rad = math.atan2(y, x)
    if ra_rad < 0:
        ra_rad += 2.0 * math.pi

    dec_rad = math.atan2(z, r_xy)
    return math.degrees(ra_rad), math.degrees(dec_rad)


# ---------------------------------------------------------------------------
# 4. Field of View (FOV) & Pixel Projections
# ---------------------------------------------------------------------------

def radec_in_fov(ra: float, dec: float, wcs_info: Dict[str, Any]) -> bool:
    """Check if celestial coordinate (RA, Dec) falls within the image FOV."""
    center_ra = float(wcs_info["center_ra"])
    center_dec = float(wcs_info["center_dec"])
    scale = float(wcs_info["scale"])  # arcsec/pixel
    width = int(wcs_info["width"])
    height = int(wcs_info["height"])

    half_w_deg = (width * scale / 3600.0) / 2.0 + FOV_MARGIN_DEG
    half_h_deg = (height * scale / 3600.0) / 2.0 + FOV_MARGIN_DEG

    if abs(dec - center_dec) > half_h_deg:
        return False

    d_ra = (ra - center_ra + 180.0) % 360.0 - 180.0
    return abs(d_ra) <= half_w_deg


def radec_to_pixel(ra: float, dec: float, wcs_info: Dict[str, Any]) -> Tuple[float, float]:
    """Project sky coordinates to image pixel space (linear approximation)."""
    center_ra = float(wcs_info["center_ra"])
    center_dec = float(wcs_info["center_dec"])
    scale = float(wcs_info["scale"])
    width = int(wcs_info["width"])
    height = int(wcs_info["height"])

    cx = width / 2.0
    cy = height / 2.0

    d_ra = (ra - center_ra + 180.0) % 360.0 - 180.0
    d_dec = dec - center_dec

    # RA increases to the left (standard sky convention), Dec increases upward
    px = cx - (d_ra * math.cos(math.radians(center_dec)) * 3600.0) / scale
    py = cy - (d_dec * 3600.0) / scale

    return round(px, 1), round(py, 1)


def _norad_id(line1: str) -> int:
    """Extract NORAD catalog ID from TLE line 1."""
    try:
        return int(line1[2:7].strip())
    except (ValueError, IndexError):
        return 0


# ---------------------------------------------------------------------------
# 5. Public Detection Interface
# ---------------------------------------------------------------------------

def find_satellites(
    wcs_info: Dict[str, Any],
    capture_time_utc: datetime,
    exposure_seconds: float = 15.0,
) -> Tuple[List[Dict[str, Any]], str, str | None]:
    """
    Identify and calculate pixel trajectory endpoints for satellites crossing the FOV.

    Returns:
        (satellites, tle_source, tle_fallback_reason) — tle_source is "cache" | "live_json" |
        "live_cdn" | "stale_cache" | "embedded_fallback". Only "stale_cache" and
        "embedded_fallback" represent degraded data; callers should treat those as a fallback.
    """
    if capture_time_utc.tzinfo is None:
        capture_time_utc = capture_time_utc.replace(tzinfo=timezone.utc)
    else:
        capture_time_utc = capture_time_utc.astimezone(timezone.utc)

    catalog, tle_source, tle_reason = fetch_tle_catalog()
    if not catalog:
        return [], tle_source, tle_reason

    trail_dt = timedelta(seconds=exposure_seconds / 2.0)
    t_start = capture_time_utc - trail_dt
    t_end = capture_time_utc + trail_dt

    width = int(wcs_info.get("width", 800))
    height = int(wcs_info.get("height", 800))

    results: List[Dict[str, Any]] = []

    for tle in catalog:
        name, line1, _ = tle

        # Propagate at center exposure time
        pos = propagate(tle, capture_time_utc)
        if pos is None:
            continue

        ra, dec = teme_to_radec(pos)

        if not radec_in_fov(ra, dec, wcs_info):
            continue

        # Build trajectory streak endpoints
        pos_start = propagate(tle, t_start) or pos
        pos_end = propagate(tle, t_end) or pos

        ra_start, dec_start = teme_to_radec(pos_start)
        ra_end, dec_end = teme_to_radec(pos_end)

        px_start = radec_to_pixel(ra_start, dec_start, wcs_info)
        px_end = radec_to_pixel(ra_end, dec_end, wcs_info)

        # Confirm at least one endpoint is in-frame
        if (
            (0 <= px_start[0] <= width and 0 <= px_start[1] <= height)
            or (0 <= px_end[0] <= width and 0 <= px_end[1] <= height)
        ):
            alt_km = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2) - EARTH_RADIUS_KM
            results.append(
                {
                    "name": name,
                    "norad_id": _norad_id(line1),
                    "start_pixel": list(px_start),
                    "end_pixel": list(px_end),
                    "altitude_km": max(0.0, alt_km),
                }
            )

    return results, tle_source, tle_reason