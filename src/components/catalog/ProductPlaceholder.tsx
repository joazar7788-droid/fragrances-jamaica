import { getBrandInitials, getBrandGradient } from "@/lib/placeholder";

interface ProductPlaceholderProps {
  brand: string;
}

export function ProductPlaceholder({ brand }: ProductPlaceholderProps) {
  const initials = getBrandInitials(brand);
  const gradient = getBrandGradient(brand);

  return (
    <div
      className="w-full h-full flex flex-col items-center justify-center relative"
      style={{ background: gradient }}
    >
      {/* Subtle border frame */}
      <div className="absolute inset-4 border border-gold/10 pointer-events-none" />

      {/* Monogram */}
      <span className="font-serif text-3xl sm:text-4xl text-gold/70 tracking-widest font-light">
        {initials}
      </span>

      {/* Brand name */}
      <span className="mt-3 text-[10px] text-text-tertiary/60 tracking-[0.25em] uppercase max-w-[80%] text-center truncate">
        {brand}
      </span>

      {/* Decorative line */}
      <div className="mt-2 w-6 h-px bg-gold/20" />
    </div>
  );
}
