"use client";

interface ActiveFiltersProps {
  filters: {
    gender: string;
    search: string;
    brand: string | null;
    types: string[];
    sizes: string[];
    priceRange: [number, number];
  };
  onClearAll: () => void;
  onRemoveGender: () => void;
  onRemoveBrand: () => void;
  onRemoveType: (type: string) => void;
  onRemoveSize: (size: string) => void;
  onResetPrice: () => void;
}

export function ActiveFilters({
  filters,
  onClearAll,
  onRemoveGender,
  onRemoveBrand,
  onRemoveType,
  onRemoveSize,
  onResetPrice,
}: ActiveFiltersProps) {
  const pills: { label: string; onRemove: () => void }[] = [];

  if (filters.gender !== "all") {
    pills.push({
      label: `Gender: ${filters.gender}`,
      onRemove: onRemoveGender,
    });
  }

  if (filters.brand) {
    pills.push({
      label: `Brand: ${filters.brand}`,
      onRemove: onRemoveBrand,
    });
  }

  filters.types.forEach((type) => {
    pills.push({
      label: type,
      onRemove: () => onRemoveType(type),
    });
  });

  filters.sizes.forEach((size) => {
    pills.push({
      label: size,
      onRemove: () => onRemoveSize(size),
    });
  });

  if (filters.priceRange[0] > 0 || filters.priceRange[1] < 1000) {
    pills.push({
      label: `$${filters.priceRange[0]}–$${filters.priceRange[1]}`,
      onRemove: onResetPrice,
    });
  }

  if (pills.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {pills.map((pill, i) => (
        <button
          key={i}
          onClick={pill.onRemove}
          className="flex items-center gap-1.5 px-2.5 py-1 bg-gold/10 border border-gold/20 rounded-full text-gold text-[11px] uppercase tracking-wider transition-all hover:bg-gold/20 group"
        >
          <span>{pill.label}</span>
          <svg className="w-3 h-3 opacity-60 group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      ))}

      {pills.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-text-tertiary text-[11px] uppercase tracking-wider hover:text-text-secondary transition-colors ml-1"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
