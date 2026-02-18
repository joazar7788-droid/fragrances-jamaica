"use client";

import { Gender } from "@/types/product";

const TABS: { value: Gender; label: string }[] = [
  { value: "all", label: "All" },
  { value: "men", label: "Men" },
  { value: "women", label: "Women" },
  { value: "unisex", label: "Unisex" },
];

interface GenderTabsProps {
  active: Gender;
  onChange: (gender: Gender) => void;
  counts: Record<string, number>;
}

export function GenderTabs({ active, onChange, counts }: GenderTabsProps) {
  return (
    <div className="flex items-center gap-1 sm:gap-2">
      {TABS.map((tab) => {
        const isActive = active === tab.value;
        const count = tab.value === "all"
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : counts[tab.value] || 0;

        return (
          <button
            key={tab.value}
            onClick={() => onChange(tab.value)}
            className={`relative px-3 sm:px-5 py-2.5 text-xs sm:text-sm uppercase tracking-[0.15em] font-medium transition-all duration-300 ${
              isActive
                ? "text-gold"
                : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            <span>{tab.label}</span>
            <span className="ml-1.5 text-[10px] opacity-50">{count}</span>

            {/* Active underline */}
            <div
              className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-px bg-gold transition-all duration-300 ${
                isActive ? "w-full" : "w-0"
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}
