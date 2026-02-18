"use client";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="relative group">
      {/* Search icon */}
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary transition-colors duration-300 group-focus-within:text-gold/70"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>

      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search fragrances..."
        className="w-full pl-10 pr-4 py-2.5 bg-bg-tertiary/60 border border-white/[0.06] rounded-md text-text-primary text-sm placeholder:text-text-tertiary/60 focus:outline-none focus:border-gold/30 focus:bg-bg-tertiary transition-all duration-300"
      />

      {/* Clear button */}
      {value && (
        <button
          onClick={() => onChange("")}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}

      {/* Focus underline accent */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-px bg-gold/50 transition-all duration-300 group-focus-within:w-full" />
    </div>
  );
}
