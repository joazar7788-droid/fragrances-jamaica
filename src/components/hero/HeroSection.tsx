"use client";

import { useEffect, useState } from "react";

export function HeroSection() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <section className="relative h-screen flex items-center justify-center overflow-hidden">
      {/* Dark atmospheric background with gradient */}
      <div className="absolute inset-0 bg-bg-primary">
        {/* Subtle radial glow */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            background:
              "radial-gradient(ellipse at 50% 30%, rgba(201, 169, 110, 0.08) 0%, transparent 60%)",
          }}
        />
        {/* Grain texture overlay */}
        <div className="noise-overlay absolute inset-0" />
      </div>

      {/* Decorative gold line elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-32 bg-gradient-to-b from-transparent via-gold/30 to-transparent" />
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-px h-32 bg-gradient-to-t from-transparent via-gold/30 to-transparent" />

      {/* Content */}
      <div className="relative z-10 text-center px-6">
        {/* Small decorative element */}
        <div
          className={`mx-auto mb-8 w-12 h-px bg-gold/60 transition-all duration-1000 delay-200 ${
            isVisible ? "opacity-100 scale-x-100" : "opacity-0 scale-x-0"
          }`}
        />

        {/* Brand name */}
        <h1
          className={`font-serif transition-all duration-1000 delay-300 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
          }`}
        >
          <span className="block text-5xl sm:text-7xl md:text-8xl lg:text-9xl tracking-ultrawide uppercase text-gold font-light">
            Fragrances
          </span>
          <span className="block text-3xl sm:text-4xl md:text-5xl lg:text-6xl tracking-[0.3em] uppercase text-text-primary/90 mt-1 font-light">
            Jamaica
          </span>
        </h1>

        {/* Decorative divider */}
        <div
          className={`mx-auto mt-8 mb-6 flex items-center gap-4 transition-all duration-1000 delay-500 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}
        >
          <div className="h-px w-16 bg-gradient-to-r from-transparent to-gold/40" />
          <div className="w-1.5 h-1.5 rotate-45 border border-gold/50" />
          <div className="h-px w-16 bg-gradient-to-l from-transparent to-gold/40" />
        </div>

        {/* Tagline */}
        <p
          className={`text-text-secondary text-sm sm:text-base md:text-lg tracking-[0.15em] uppercase font-light transition-all duration-1000 delay-600 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          Jamaica&apos;s Premier Fragrance Collection
        </p>

        {/* CTA */}
        <a
          href="#catalog"
          className={`mt-12 inline-block px-10 py-3.5 border border-gold/50 text-gold uppercase tracking-[0.2em] text-xs sm:text-sm font-medium transition-all duration-500 delay-700 hover:bg-gold hover:text-bg-primary hover:border-gold ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          Explore Collection
        </a>
      </div>

      {/* Scroll indicator */}
      <div
        className={`absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 transition-all duration-1000 delay-1000 ${
          isVisible ? "opacity-60" : "opacity-0"
        }`}
      >
        <span className="text-text-tertiary text-[10px] tracking-[0.3em] uppercase">
          Scroll
        </span>
        <div className="w-px h-8 bg-gradient-to-b from-gold/40 to-transparent animate-pulse" />
      </div>
    </section>
  );
}
