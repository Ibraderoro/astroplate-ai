"""
CelesTrak TLE satellite orbit tracker.

Fetches the full active satellite catalog, propagates each orbit with sgp4,
and identifies satellites whose projected position falls inside the plate-solved
field of view at the given capture time.

Returns a list of dicts matching the SatellitePass schema shape.
"""

import math
from datetime import datetime, timedelta

import requests
from sgp4.api import Satrec, jday

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CELESTRAK_TLE_URL = "https://celestrak.org/pub/TLE/catalog.txt"
EARTH_RADIUS_KM = 6371.0
FOV_MARGIN_DEG = 0.1  # extra padding around FOV bounding box


# ---------------------------------------------------------------------------
# 1. TLE catalog fetch and parse
# ---------------------------------------------------------------------------

def fetch_tle_catalog() -> list[tuple[str, str, str]]:
    """Fetch CelesTrak catalog.txt and parse into (name, line1, line2) tuples."""
    resp = requests.get(CELESTRAK_TLE_URL, timeout=30)
    resp.raise_for_status()

    raw_lines = [line.rstrip() for line in resp.text.splitlines()]
    # Filter out blank lines, then group into triplets
    lines = [l for l in raw_lines if l]

    catalog: list[tuple[str, str, str]] = []
    i = 0
    while i + 2 < len(lines):
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()
        # Basic sanity: TLE lines start with '1' and '2'
        if line1.startswith("1 ") and line2.startswith("2 "):
            catalog.append((name, line1, line2))
            i += 3
        else:
            i += 1  # re-sync on malformed entries

    return catalog


# ---------------------------------------------------------------------------
# 2. Orbit propagation
# ---------------------------------------------------------------------------

def _datetime_to_jd(t: datetime) -> tuple[float, float]:
    """Convert a UTC datetime to (jd, fr) Julian date pair for sgp4."""
    return jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)


def propagate(
    tle_tuple: tuple[str, str, str],
    t_utc: datetime,
) -> tuple[float, float, float] | None:
    """Propagate TLE to t_utc. Returns TEME position (km) or None on error."""
    _, line1, line2 = tle_tuple
    try:
        sat = Satrec.twoline2rv(line1, line2)
    except Exception:
        return None

    jd, fr = _datetime_to_jd(t_utc)
    e, r, _ = sat.sgp4(jd, fr)

    if e != 0:
        return None
    return (r[0], r[1], r[2])


# ---------------------------------------------------------------------------
# 3. TEME → RA/Dec (simple equatorial approximation)
# ---------------------------------------------------------------------------

def _julian_day(t: datetime) -> float:
    """Compute Julian Day Number for a UTC datetime."""
    y, m, d = t.year, t.month, t.day
    h = t.hour + t.minute / 60.0 + (t.second + t.microsecond / 1e6) / 3600.0
    if m <= 2:
        y -= 1
        m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + h / 24.0 + B - 1524.5


def teme_to_radec(
    pos_teme: tuple[float, float, float],
    t_utc: datetime,
) -> tuple[float, float]:
    """Convert TEME Cartesian position to RA/Dec (degrees) via GMST rotation."""
    x, y, z = pos_teme

    jd_ut1 = _julian_day(t_utc)
    # GMST in degrees
    gmst_deg = (280.46061837 + 360.98564736629 * (jd_ut1 - 2451545.0)) % 360.0
    gmst_rad = math.radians(gmst_deg)

    # Rotate TEME x, y by GMST to equatorial frame
    x_eq = x * math.cos(gmst_rad) + y * math.sin(gmst_rad)
    y_eq = -x * math.sin(gmst_rad) + y * math.cos(gmst_rad)

    ra_rad = math.atan2(y_eq, x_eq)
    ra_deg = math.degrees(ra_rad) % 360.0

    r_xy = math.sqrt(x_eq**2 + y_eq**2)
    dec_deg = math.degrees(math.atan2(z, r_xy))

    return (ra_deg, dec_deg)


# ---------------------------------------------------------------------------
# 4. FOV bounding-box test (with RA wraparound handling)
# ---------------------------------------------------------------------------

def radec_in_fov(ra: float, dec: float, wcs_info: dict) -> bool:
    """Return True if (ra, dec) falls within the plate-solved FOV."""
    center_ra: float = wcs_info["center_ra"]
    center_dec: float = wcs_info["center_dec"]
    scale: float = wcs_info["scale"]  # arcsec/pixel
    width: int = wcs_info["width"]
    height: int = wcs_info["height"]

    half_w_deg = (width * scale / 3600.0) / 2.0 + FOV_MARGIN_DEG
    half_h_deg = (height * scale / 3600.0) / 2.0 + FOV_MARGIN_DEG

    # Dec check (straightforward)
    if abs(dec - center_dec) > half_h_deg:
        return False

    # RA check with wraparound
    d_ra = (ra - center_ra + 180.0) % 360.0 - 180.0
    return abs(d_ra) <= half_w_deg


# ---------------------------------------------------------------------------
# 5. RA/Dec → pixel projection (linear approximation)
# ---------------------------------------------------------------------------

def radec_to_pixel(ra: float, dec: float, wcs_info: dict) -> tuple[float, float]:
    """Project sky coordinates to image pixel coordinates."""
    center_ra: float = wcs_info["center_ra"]
    center_dec: float = wcs_info["center_dec"]
    scale: float = wcs_info["scale"]  # arcsec/pixel
    width: int = wcs_info["width"]
    height: int = wcs_info["height"]

    cx = width / 2.0
    cy = height / 2.0

    # RA delta with wraparound (degrees)
    d_ra = (ra - center_ra + 180.0) % 360.0 - 180.0
    d_dec = dec - center_dec

    px = cx + d_ra * 3600.0 / scale
    py = cy - d_dec * 3600.0 / scale  # y-axis flipped (Dec increases up, pixels down)

    return (px, py)


# ---------------------------------------------------------------------------
# 6. Altitude helper
# ---------------------------------------------------------------------------

def _altitude_km(pos_teme: tuple[float, float, float]) -> float:
    """Compute satellite altitude above Earth's surface in km."""
    x, y, z = pos_teme
    return math.sqrt(x**2 + y**2 + z**2) - EARTH_RADIUS_KM


# ---------------------------------------------------------------------------
# 7. NORAD ID extraction from TLE line 1
# ---------------------------------------------------------------------------

def _norad_id(line1: str) -> int:
    """Extract NORAD catalog number from TLE line 1 (chars 2–6)."""
    try:
        return int(line1[2:7].strip())
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# 8. Main public function
# ---------------------------------------------------------------------------

def find_satellites(wcs_info: dict, capture_time_utc: datetime) -> list[dict]:
    """
    Identify satellites in the plate-solved FOV at capture_time_utc.

    Args:
        wcs_info: dict with keys center_ra, center_dec, scale, width, height
                  (as returned by plate_solver.solve())
        capture_time_utc: observation time in UTC

    Returns:
        List of dicts matching SatellitePass schema:
        {name, norad_id, start_pixel, end_pixel, altitude_km}
    """
    catalog = fetch_tle_catalog()

    trail_dt = timedelta(seconds=30)
    t_start = capture_time_utc - trail_dt
    t_end = capture_time_utc + trail_dt

    results: list[dict] = []

    for tle in catalog:
        name, line1, line2 = tle

        # Propagate at observation time
        pos = propagate(tle, capture_time_utc)
        if pos is None:
            continue

        ra, dec = teme_to_radec(pos, capture_time_utc)

        if not radec_in_fov(ra, dec, wcs_info):
            continue

        # Build trail endpoints
        pos_start = propagate(tle, t_start) or pos
        pos_end = propagate(tle, t_end) or pos

        ra_start, dec_start = teme_to_radec(pos_start, t_start)
        ra_end, dec_end = teme_to_radec(pos_end, t_end)

        px_start = radec_to_pixel(ra_start, dec_start, wcs_info)
        px_end = radec_to_pixel(ra_end, dec_end, wcs_info)

        results.append(
            {
                "name": name,
                "norad_id": _norad_id(line1),
                "start_pixel": list(px_start),
                "end_pixel": list(px_end),
                "altitude_km": _altitude_km(pos),
            }
        )

    return results
