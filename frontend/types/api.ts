/** TypeScript interfaces mirroring backend Pydantic models. */

export interface StarAnnotation {
  x: number;
  y: number;
  width: number;
  height: number;
  ra: number;
  dec: number;
}

export interface SatellitePass {
  name: string;
  norad_id: number;
  /** [x, y] pixel coordinates */
  start_pixel: [number, number];
  /** [x, y] pixel coordinates */
  end_pixel: [number, number];
  altitude_km: number;
}

export interface ExplanationTiers {
  kid: string;
  adult: string;
  astrophysicist: string;
}

export interface AnalyzeResponse {
  image_width: number;
  image_height: number;
  stars: StarAnnotation[];
  satellites: SatellitePass[];
  explanations: ExplanationTiers;
  plate_center_ra: number;
  plate_center_dec: number;
  plate_scale_arcsec_per_pixel: number;
}
