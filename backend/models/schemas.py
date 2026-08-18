from pydantic import BaseModel


class StarAnnotation(BaseModel):
    x: float
    y: float
    width: float
    height: float
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
    image_width: int
    image_height: int
    stars: list[StarAnnotation]
    satellites: list[SatellitePass]
    explanations: ExplanationTiers
    plate_center_ra: float
    plate_center_dec: float
    plate_scale_arcsec_per_pixel: float
