from typing import Literal, Optional
from pydantic import BaseModel, Field


class StarAnnotation(BaseModel):
    x: float
    y: float
    width: float = 24.0
    height: float = 24.0
    ra: float
    dec: float


class SatellitePass(BaseModel):
    name: str
    norad_id: int
    start_pixel: list[float]
    end_pixel: list[float]
    altitude_km: float


class ExplanationTiers(BaseModel):
    kid: str
    adult: str
    astrophysicist: str


class AnalyzeResponse(BaseModel):
    source: Literal["live", "fallback"] = Field(
        ...,
        description="Data provenance: 'live' indicates genuine execution; 'fallback' indicates simulated fallback data.",
    )
    fallback_reason: Optional[str] = Field(
        None,
        description="Explains why fallback mode was triggered (e.g. Astrometry queue timeout, unconfigured API credentials).",
    )
    image_width: int
    image_height: int
    stars: list[StarAnnotation]
    satellites: list[SatellitePass]
    explanations: ExplanationTiers
    plate_center_ra: float
    plate_center_dec: float
    plate_scale_arcsec_per_pixel: float