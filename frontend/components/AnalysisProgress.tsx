'use client';

import {
  CheckCircle2,
  Circle,
  Crosshair,
  Loader2,
  Satellite,
  Sparkles,
  UploadCloud,
} from 'lucide-react';

interface Props {
  currentStep: string;
}

const PIPELINE_STEPS = [
  {
    id: 'upload',
    title: 'Uploading & Reading Frame',
    description: 'Extracting metadata and preparing pixel matrix...',
    icon: UploadCloud,
  },
  {
    id: 'astrometry',
    title: 'Astrometry.net Plate-Solving',
    description:
      'Matching asterisms against Gaia/Tycho-2 catalog quad trees...',
    icon: Crosshair,
  },
  {
    id: 'satellites',
    title: 'Orbital Satellite Tracking',
    description: 'Propagating CelesTrak SGP4 ephemerides across the FOV...',
    icon: Satellite,
  },
  {
    id: 'granite',
    title: 'Granite Multi-Tier Reasoning',
    description: 'Synthesizing Kid, Adult, and Astrophysicist explanations...',
    icon: Sparkles,
  },
];

type StepStatus = 'done' | 'current' | 'pending';

const STEP_CLASSES: Record<StepStatus, { container: string; icon: string; title: string }> = {
  done:    { container: 'border-gray-800/60 bg-gray-900/30 opacity-70', icon: 'text-emerald-400', title: 'text-gray-300' },
  current: { container: 'border-blue-500/50 bg-blue-950/20',            icon: 'text-blue-400',    title: 'text-white'    },
  pending: { container: 'border-transparent bg-transparent opacity-30', icon: 'text-gray-500',    title: 'text-gray-500' },
};

const getStatus = (idx: number, activeIndex: number): StepStatus =>
  idx < activeIndex ? 'done' : idx === activeIndex ? 'current' : 'pending';

function StepIcon({ isDone, isCurrent }: { isDone: boolean; isCurrent: boolean }) {
  if (isDone)    return <CheckCircle2 className='h-4 w-4 text-emerald-400' />;
  if (isCurrent) return <Loader2      className='h-4 w-4 animate-spin text-blue-400' />;
  return               <Circle        className='h-4 w-4 text-gray-600' />;
}

interface PipelineStepProps {
  step: (typeof PIPELINE_STEPS)[number];
  status: StepStatus;
}

function PipelineStep({ step, status }: PipelineStepProps) {
  const cls = STEP_CLASSES[status];
  const Icon = step.icon;
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-3 transition-all duration-300 ${cls.container}`}
    >
      <div className='mt-0.5 shrink-0'>
        <StepIcon isDone={status === 'done'} isCurrent={status === 'current'} />
      </div>
      <div className='flex-1'>
        <div className='flex items-center gap-2'>
          <Icon className={`h-3.5 w-3.5 ${cls.icon}`} />
          <span className={`text-xs font-medium ${cls.title}`}>{step.title}</span>
        </div>
        <p className='mt-0.5 text-[11px] text-gray-400'>{step.description}</p>
      </div>
    </div>
  );
}

export default function AnalysisProgress({ currentStep }: Props) {
  const currentIndex = PIPELINE_STEPS.findIndex((s) => s.id === currentStep);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className='w-full rounded-xl border border-gray-800 bg-gray-900/90 p-5 shadow-xl backdrop-blur-md'>
      <div className='mb-4 flex items-center justify-between border-b border-gray-800 pb-3'>
        <div>
          <h4 className='text-sm font-semibold text-white'>
            Live Pipeline Execution
          </h4>
          <p className='text-xs text-gray-400'>
            Receiving real-time SSE telemetry from backend
          </p>
        </div>
        <div className='flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400'>
          <Loader2 className='h-3 w-3 animate-spin' />
          <span>
            Stage {activeIndex + 1} of {PIPELINE_STEPS.length}
          </span>
        </div>
      </div>

      <div className='space-y-3'>
        {PIPELINE_STEPS.map((step, idx) => (
          <PipelineStep key={step.id} step={step} status={getStatus(idx, activeIndex)} />
        ))}
      </div>
    </div>
  );
}
