"use client";

import { Atom, Rocket, Telescope } from "lucide-react";
import { useState } from "react";
import type { ExplanationTiers } from "@/types/api";

interface Props {
  explanations: ExplanationTiers;
}

type Tier = keyof ExplanationTiers;

const TABS: { id: Tier; label: string; Icon: React.ElementType }[] = [
  { id: "kid", label: "Kid", Icon: Rocket },
  { id: "adult", label: "Adult", Icon: Telescope },
  { id: "astrophysicist", label: "Astrophysicist", Icon: Atom },
];

export default function ExplanationCard({ explanations }: Props) {
  const [active, setActive] = useState<Tier>("kid");

  return (
    <div className="flex flex-col rounded-xl border border-gray-700 bg-gray-900 overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-gray-700">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setActive(id)}
            className={`
              flex flex-1 items-center justify-center gap-2 py-3 text-sm font-medium transition-colors
              ${active === id
                ? "border-b-2 border-blue-400 bg-gray-800 text-blue-300"
                : "text-gray-400 hover:bg-gray-800/50 hover:text-gray-200"
              }
            `}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {TABS.map(({ id }) => (
          <div
            key={id}
            className={active === id ? "block" : "hidden"}
            role="tabpanel"
          >
            <p className="text-sm leading-relaxed text-gray-300">
              {explanations[id] || (
                <span className="italic text-gray-500">No explanation available.</span>
              )}
            </p>
          </div>
        ))}
      </div>

      {/* Tier label badge */}
      <div className="border-t border-gray-700 px-5 py-2">
        <span className="text-xs text-gray-500">
          {active === "kid" && "✦ Simplified for curious minds"}
          {active === "adult" && "✦ Accessible science summary"}
          {active === "astrophysicist" && "✦ Technical field report — IBM Granite"}
        </span>
      </div>
    </div>
  );
}
