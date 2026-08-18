'use client';

import { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import type { SatellitePass, StarAnnotation } from '@/types/api';

export interface SkyCanvasRef {
  exportPNG: () => void;
}

interface Props {
  imageSrc: string;
  stars: StarAnnotation[];
  satellites: SatellitePass[];
}

interface TooltipState {
  x: number;
  y: number;
  ra: number;
  dec: number;
}

const SkyCanvas = forwardRef<SkyCanvasRef, Props>(
  ({ imageSrc, stars = [], satellites = [] }, ref) => {
    const imgRef = useRef<HTMLImageElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [tooltip, setTooltip] = useState<TooltipState | null>(null);
    const [imgSize, setImgSize] = useState<{ width: number; height: number }>({
      width: 800,
      height: 600,
    });

    // ------------------------------------------------------------------
    // PNG Export (Generates high-res merged image on offscreen canvas)
    // ------------------------------------------------------------------
    useImperativeHandle(ref, () => ({
      exportPNG: () => {
        const img = imgRef.current;
        if (!img) return;

        const offscreen = document.createElement('canvas');
        offscreen.width = img.naturalWidth || imgSize.width;
        offscreen.height = img.naturalHeight || imgSize.height;
        const ctx = offscreen.getContext('2d');
        if (!ctx) return;

        // 1. Draw source image
        ctx.drawImage(img, 0, 0, offscreen.width, offscreen.height);

        // 2. Draw star bounding boxes
        ctx.lineWidth = Math.max(2, Math.floor(offscreen.width / 400));
        ctx.strokeStyle = 'rgba(250, 204, 21, 0.9)'; // yellow-400
        stars.forEach((star) => {
          ctx.strokeRect(star.x, star.y, star.width || 24, star.height || 24);
        });

        // 3. Draw satellite streaks
        ctx.lineWidth = Math.max(3, Math.floor(offscreen.width / 300));
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.95)'; // red-500
        ctx.fillStyle = 'rgba(254, 202, 202, 0.95)';
        ctx.font = `bold ${Math.max(12, Math.floor(offscreen.width / 60))}px sans-serif`;

        satellites.forEach((sat) => {
          const [sx, sy] = sat.start_pixel;
          const [ex, ey] = sat.end_pixel;
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(ex, ey);
          ctx.stroke();
          ctx.fillText(sat.name, (sx + ex) / 2, (sy + ey) / 2 - 6);
        });

        const link = document.createElement('a');
        link.href = offscreen.toDataURL('image/png');
        link.download = `astroplate_annotated_${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      },
    }));

    // Update natural coordinate space once image loads
    const handleImageLoad = () => {
      if (imgRef.current) {
        setImgSize({
          width: imgRef.current.naturalWidth || 800,
          height: imgRef.current.naturalHeight || 600,
        });
      }
    };

    // Hover detection for interactive RA/Dec tooltip
    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
      const img = imgRef.current;
      if (!img) return;

      const rect = img.getBoundingClientRect();
      const scaleX = imgSize.width / rect.width;
      const scaleY = imgSize.height / rect.height;

      const mouseX = (e.clientX - rect.left) * scaleX;
      const mouseY = (e.clientY - rect.top) * scaleY;

      const hit = stars.find((s) => {
        const w = s.width || 24;
        const h = s.height || 24;
        return (
          mouseX >= s.x &&
          mouseX <= s.x + w &&
          mouseY >= s.y &&
          mouseY <= s.y + h
        );
      });

      if (hit) {
        const containerRect = containerRef.current?.getBoundingClientRect();
        setTooltip({
          x: e.clientX - (containerRect?.left ?? 0) + 14,
          y: e.clientY - (containerRect?.top ?? 0) - 10,
          ra: hit.ra,
          dec: hit.dec,
        });
      } else {
        setTooltip(null);
      }
    };

    return (
      <div
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
        className='relative overflow-hidden rounded-xl border border-gray-700 bg-gray-950 w-full select-none'
      >
        {/* Base Astrophotography Frame */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef}
          src={imageSrc}
          alt='Astrometric Target Frame'
          onLoad={handleImageLoad}
          className='block w-full h-auto object-contain'
        />

        {/* Scaled Overlay SVG (Star Boxes & Satellite Trails) */}
        <svg
          viewBox={`0 0 ${imgSize.width} ${imgSize.height}`}
          className='pointer-events-none absolute inset-0 h-full w-full'
        >
          {/* Star Bounding Boxes */}
          {stars.map((star, idx) => (
            <g key={`star-${idx}`}>
              <rect
                x={star.x}
                y={star.y}
                width={star.width || 24}
                height={star.height || 24}
                fill='none'
                stroke='#facc15'
                strokeWidth={Math.max(2, imgSize.width / 400)}
                className='transition-all hover:stroke-yellow-200'
              />
            </g>
          ))}

          {/* Satellite Streaks */}
          {satellites.map((sat, idx) => {
            const [sx, sy] = sat.start_pixel;
            const [ex, ey] = sat.end_pixel;
            return (
              <g key={`sat-${idx}`}>
                <line
                  x1={sx}
                  y1={sy}
                  x2={ex}
                  y2={ey}
                  stroke='#ef4444'
                  strokeWidth={Math.max(2.5, imgSize.width / 300)}
                  strokeLinecap='round'
                />
                <text
                  x={(sx + ex) / 2}
                  y={(sy + ey) / 2 - 8}
                  fill='#fca5a5'
                  fontSize={Math.max(12, Math.floor(imgSize.width / 60))}
                  fontWeight='bold'
                  textAnchor='middle'
                >
                  {sat.name}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover RA/Dec Tooltip */}
        {tooltip && (
          <div
            className='pointer-events-none absolute z-20 rounded bg-gray-950/90 border border-yellow-500/60 px-2.5 py-1 text-xs font-mono text-yellow-300 shadow-xl backdrop-blur-sm'
            style={{ left: tooltip.x, top: tooltip.y }}
          >
            RA {tooltip.ra.toFixed(4)}° · Dec {tooltip.dec.toFixed(4)}°
          </div>
        )}

        {/* Overlay Legend */}
        <div className='absolute bottom-3 right-3 flex items-center gap-3 rounded-lg border border-gray-800 bg-black/80 px-3 py-1.5 text-xs backdrop-blur-sm'>
          <span className='flex items-center gap-1.5'>
            <span className='inline-block h-2.5 w-3.5 border border-yellow-400' />
            <span className='text-gray-300'>Stars ({stars.length})</span>
          </span>
          <span className='flex items-center gap-1.5'>
            <span className='inline-block h-0.5 w-3.5 bg-red-500' />
            <span className='text-gray-300'>
              Satellites ({satellites.length})
            </span>
          </span>
        </div>
      </div>
    );
  },
);

SkyCanvas.displayName = 'SkyCanvas';
export default SkyCanvas;
