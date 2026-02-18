"use client";

interface FilterChipsProps {
  label: string;
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
}

export function FilterChips({ label, options, selected, onToggle }: FilterChipsProps) {
  return (
    <div>
      <span className="text-text-tertiary text-[10px] uppercase tracking-[0.15em] mb-2 block">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const isSelected = selected.includes(option);
          return (
            <button
              key={option}
              onClick={() => onToggle(option)}
              className={`px-2.5 py-1 text-[11px] uppercase tracking-wider rounded-sm border transition-all duration-200 ${
                isSelected
                  ? "bg-gold/15 border-gold/40 text-gold"
                  : "bg-transparent border-white/[0.08] text-text-tertiary hover:border-white/15 hover:text-text-secondary"
              }`}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}
