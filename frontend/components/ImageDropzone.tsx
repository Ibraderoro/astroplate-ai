'use client';

import { UploadCloud } from 'lucide-react';
import Image from 'next/image';
import { useCallback, useRef, useState } from 'react';
import type { AnalyzeResponse } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const EVENT_RE = /^event:\s*(.+)$/m;
const DATA_RE = /^data:\s*(.+)$/m;

interface SseMessage {
  eventType: string;
  data: unknown;
}

function parseSseMessages(blocks: string[]): SseMessage[] {
  const messages: SseMessage[] = [];

  for (const block of blocks) {
    const dataMatch = DATA_RE.exec(block);
    if (!dataMatch) continue;
    const eventMatch = EVENT_RE.exec(block);
    messages.push({
      eventType: eventMatch ? eventMatch[1].trim() : 'message',
      data: JSON.parse(dataMatch[1].trim()),
    });
  }

  return messages;
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

const PRESETS = [
  { label: 'Orion Nebula', filename: 'orion_nebula.jpg' },
  { label: 'Andromeda', filename: 'andromeda.jpg' },
  { label: 'Pleiades', filename: 'pleiades.jpg' },
];

interface Props {
  onResult: (data: AnalyzeResponse, imageSrc: string) => void;
  onLoading: (loading: boolean) => void;
  onStepChange: (step: string) => void;
}

export default function ImageDropzone({
  onResult,
  onLoading,
  onStepChange,
}: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      onLoading(true);
      onStepChange('upload');

      try {
        // Convert to permanent base64 data URL
        const base64Src = await fileToDataUrl(file);

        const form = new FormData();
        form.append('file', file);

        const res = await fetch(`${API_BASE}/analyze`, {
          method: 'POST',
          body: form,
        });

        if (!res.ok || !res.body) {
          throw new Error(`Server returned status ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const pending = buffer.split('\n\n');
          buffer = pending.pop() ?? '';

          for (const msg of parseSseMessages(pending)) {
            if (msg.eventType === 'progress') {
              onStepChange((msg.data as { step: string }).step);
            } else if (msg.eventType === 'complete') {
              onResult(msg.data as AnalyzeResponse, base64Src);
            }
          }
        }
      } catch (err) {
        console.error('[ImageDropzone] analyze failed:', err);
        alert(`Analysis failed: ${(err as Error).message}`);
      } finally {
        onLoading(false);
      }
    },
    [onLoading, onResult, onStepChange],
  );

  const handlePreset = async (filename: string) => {
    try {
      const res = await fetch(`/presets/${filename}`);
      if (!res.ok) throw new Error(`Could not load preset: ${filename}`);
      const blob = await res.blob();
      const file = new File([blob], filename, {
        type: blob.type || 'image/jpeg',
      });
      await handleFile(file);
    } catch (err) {
      console.error('[ImageDropzone] preset failed:', err);
      alert(`Failed to process preset: ${(err as Error).message}`);
    }
  };

  return (
    <div className='flex flex-col gap-4'>
      <div
        role='button'
        tabIndex={0}
        aria-label='Upload astronomical image'
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
        className={`
          flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed
          px-6 py-10 text-center transition-colors
          ${
            dragging
              ? 'border-blue-400 bg-blue-950/30'
              : 'border-gray-700 bg-gray-900 hover:border-gray-500 hover:bg-gray-800/50'
          }
        `}
      >
        <UploadCloud className='h-10 w-10 text-gray-500' />
        <div>
          <p className='text-sm font-medium text-gray-300'>
            Drop an astronomical image here
          </p>
          <p className='mt-1 text-xs text-gray-500'>
            JPEG, PNG, or FITS preview
          </p>
        </div>
        <input
          ref={inputRef}
          type='file'
          accept='image/jpeg,image/png'
          className='hidden'
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = '';
          }}
        />
      </div>

      <div>
        <p className='mb-2 text-xs font-medium uppercase tracking-wider text-gray-500'>
          Or choose a preset
        </p>
        <div className='grid grid-cols-3 gap-2'>
          {PRESETS.map(({ label, filename }) => (
            <button
              type='button'
              key={filename}
              onClick={() => handlePreset(filename)}
              className='group relative overflow-hidden rounded-lg border border-gray-700 bg-gray-800 p-0 transition-colors hover:border-blue-500'
              title={label}
            >
              <div className='relative h-20 w-full bg-gray-900'>
                <Image
                  src={`/presets/${filename}`}
                  alt={label}
                  fill
                  className='object-cover opacity-70 transition-opacity group-hover:opacity-100'
                  sizes='(max-width: 768px) 33vw, 120px'
                />
              </div>
              <p className='py-1 text-center text-xs text-gray-400 group-hover:text-white'>
                {label}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
