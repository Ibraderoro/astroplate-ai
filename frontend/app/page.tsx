'use client';

import {
  AlertTriangle,
  CheckCircle2,
  FileJson,
  ImageDown,
  Info,
} from 'lucide-react';
import { useRef, useState } from 'react';
import AnalysisProgress from '@/components/AnalysisProgress';
import ExplanationCard from '@/components/ExplanationCard';
import ImageDropzone from '@/components/ImageDropzone';
import SkyCanvas, { type SkyCanvasRef } from '@/components/SkyCanvas';
import type { AnalyzeResponse } from '@/types/api';

export default function Home() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [imageSrc, setImageSrc] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>('upload');

  const canvasRef = useRef<SkyCanvasRef>(null);

  const handleResult = (data: AnalyzeResponse, src: string) => {
    setImageSrc(src);
    setResult(data);
  };

  const handleExportJSON = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `astroplate_analysis_${result.source}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className='flex flex-col gap-8'>
      {/* Header */}
      <div className='flex flex-col gap-3 md:flex-row md:items-center md:justify-between'>
        <div>
          <h2 className='text-2xl font-bold tracking-tight text-white'>
            Sky Analyser
          </h2>
          <p className='mt-1 text-sm text-gray-400'>
            Upload an astronomical image or choose a preset — AstroPlate AI will
            plate-solve, detect satellite streaks, and explain what's in the
            field.
          </p>
        </div>

        {/* Data Provenance Badge */}
        {result && !loading && (
          <div className='shrink-0'>
            {result.source === 'live' ? (
              <span className='inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-950/60 px-3 py-1 text-xs font-medium text-emerald-400'>
                <CheckCircle2 className='h-3.5 w-3.5' />
                Live Solution
              </span>
            ) : (
              <span className='inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-950/60 px-3 py-1 text-xs font-medium text-amber-300'>
                <AlertTriangle className='h-3.5 w-3.5' />
                Demo Simulated Mode
              </span>
            )}
          </div>
        )}
      </div>

      {/* Top row: Dropzone and Progress Stepper */}
      <section className='grid grid-cols-1 gap-6 lg:grid-cols-12'>
        <div className='lg:col-span-5 max-w-md w-full'>
          <ImageDropzone
            onResult={handleResult}
            onLoading={setLoading}
            onStepChange={setCurrentStep}
          />
        </div>

        {loading && (
          <div className='lg:col-span-7 flex items-start'>
            <AnalysisProgress currentStep={currentStep} />
          </div>
        )}
      </section>

      {/* Fallback / Graceful Degradation Notice */}
      {result && result.source === 'fallback' && !loading && (
        <div className='flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 text-amber-200'>
          <Info className='h-5 w-5 shrink-0 text-amber-400 mt-0.5' />
          <div className='text-xs space-y-1'>
            <p className='font-semibold text-amber-300'>
              Graceful Degradation Notice
            </p>
            <p className='text-amber-200/80'>
              {result.fallback_reason
                ? `Live astrometric pipeline degraded: ${result.fallback_reason}.`
                : 'Live solving was unavailable for this frame.'}{' '}
              Displaying simulated catalog match and synthetic Granite reasoning
              for interactive demonstration.
            </p>
          </div>
        </div>
      )}

      {/* Results View */}
      {result && !loading && (
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-3'>
          <div className='lg:col-span-2 flex flex-col gap-3'>
            <div className='flex items-center justify-between'>
              <h3 className='text-sm font-semibold uppercase tracking-wider text-gray-400'>
                Sky Canvas
              </h3>
              <div className='flex items-center gap-2'>
                <button
                  type='button'
                  onClick={() => canvasRef.current?.exportPNG()}
                  className='flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-200 transition-colors hover:border-gray-500 hover:bg-gray-700'
                >
                  <ImageDown className='h-3.5 w-3.5 text-yellow-400' />
                  <span>Export PNG</span>
                </button>
                <button
                  type='button'
                  onClick={handleExportJSON}
                  className='flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-200 transition-colors hover:border-gray-500 hover:bg-gray-700'
                >
                  <FileJson className='h-3.5 w-3.5 text-blue-400' />
                  <span>Export JSON</span>
                </button>
              </div>
            </div>

            <SkyCanvas
              ref={canvasRef}
              imageSrc={imageSrc}
              stars={result.stars}
              satellites={result.satellites}
            />

            <dl className='grid grid-cols-3 gap-3'>
              {[
                {
                  label: 'Center RA',
                  value: `${result.plate_center_ra.toFixed(4)}°`,
                },
                {
                  label: 'Center Dec',
                  value: `${result.plate_center_dec.toFixed(4)}°`,
                },
                {
                  label: 'Plate scale',
                  value: `${result.plate_scale_arcsec_per_pixel.toFixed(3)} ″/px`,
                },
              ].map(({ label, value }) => (
                <div key={label} className='rounded-lg bg-gray-800 px-3 py-2'>
                  <dt className='text-xs text-gray-500'>{label}</dt>
                  <dd className='mt-0.5 text-sm font-mono text-gray-200'>
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <div className='flex flex-col gap-4'>
            <h3 className='text-sm font-semibold uppercase tracking-wider text-gray-400'>
              AI Explanations
            </h3>
            <ExplanationCard explanations={result.explanations} />

            {result.satellites.length > 0 && (
              <div className='rounded-xl border border-gray-700 bg-gray-900 p-4'>
                <h4 className='mb-2 text-xs font-semibold uppercase tracking-wider text-red-400'>
                  Satellites Detected ({result.satellites.length})
                </h4>
                <ul className='space-y-1.5'>
                  {result.satellites.map((sat) => (
                    <li
                      key={sat.norad_id}
                      className='flex justify-between text-xs'
                    >
                      <span className='font-medium text-gray-300'>
                        {sat.name}
                      </span>
                      <span className='text-gray-500'>
                        NORAD {sat.norad_id} · {sat.altitude_km.toFixed(0)} km
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
