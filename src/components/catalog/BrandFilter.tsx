"use client";

import { useState, useRef, useEffect } from "react";
import { Brand } from "@/types/product";

interface BrandFilterProps {
  brands: Brand[];
  selected: string | null;
  onChange: (brand: string | null) => void;
}

export function BrandFilter({ brands, selected, onChange }: BrandFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredBrands = query
    ? brands.filter((b) => b.name.toLowerCase().includes(query.toLowerCase()))
    : brands;

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <div
        className="flex items-center gap-2 px-3 py-2.5 bg-bg-tertiary/60 border border-white/[0.06] rounded-md cursor-pointer transition-all duration-300 hover:border-gold/20"
        onClick={() => {
          setIsOpen(!isOpen);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
      >
        <svg className="w-4 h-4 text-text-tertiary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
        <span className={`text-sm ${selected ? "text-gold" : "text-text-tertiary/70"}`}>
          {selected || "All Brands"}
        </span>
        {selected && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onChange(null);
              setQuery("");
            }}
            className="ml-auto text-text-tertiary hover:text-text-secondary"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full min-w-[240px] max-h-72 bg-bg-elevated border border-white/[0.08] rounded-md shadow-xl overflow-hidden">
          {/* Search input */}
          <div className="p-2 border-b border-white/[0.06]">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search brands..."
              className="w-full px-3 py-1.5 bg-bg-tertiary/80 text-text-primary text-sm rounded placeholder:text-text-tertiary/50 focus:outline-none"
            />
          </div>

          {/* Brand list */}
          <div className="overflow-y-auto max-h-56">
            {filteredBrands.length === 0 ? (
              <div className="px-4 py-3 text-text-tertiary text-sm">No brands found</div>
            ) : (
              filteredBrands.map((brand) => (
                <button
                  key={brand.name}
                  onClick={() => {
                    onChange(brand.name);
                    setIsOpen(false);
                    setQuery("");
                  }}
                  className={`w-full flex items-center justify-between px-4 py-2 text-sm transition-colors hover:bg-bg-tertiary/60 ${
                    selected === brand.name ? "text-gold" : "text-text-secondary"
                  }`}
                >
                  <span className="truncate">{brand.name}</span>
                  <span className="text-[10px] text-text-tertiary ml-2 shrink-0">{brand.count}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
