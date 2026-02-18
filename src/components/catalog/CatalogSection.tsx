"use client";

import { useState, useMemo } from "react";
import { Product, Brand } from "@/types/product";
import { useProducts } from "@/hooks/useProducts";
import { GenderTabs } from "./GenderTabs";
import { SearchBar } from "./SearchBar";
import { BrandFilter } from "./BrandFilter";
import { FilterChips } from "./FilterChips";
import { PriceRangeSlider } from "./PriceRangeSlider";
import { SortDropdown } from "./SortDropdown";
import { ActiveFilters } from "./ActiveFilters";
import { ProductGrid } from "./ProductGrid";
import { ProductModal } from "./ProductModal";

interface CatalogSectionProps {
  products: Product[];
  brands: Brand[];
}

// Common fragrance types and sizes for the filter chips
const FRAG_TYPES = ["EDP", "EDT", "Parfum", "EDC", "Cologne"];
const COMMON_SIZES = ["1 oz", "1.7 oz", "2.5 oz", "3.4 oz", "4.2 oz", "5 oz", "6.7 oz"];

export function CatalogSection({ products, brands }: CatalogSectionProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const {
    filteredProducts,
    filters,
    setGender,
    setSearch,
    setBrand,
    setPriceRange,
    toggleType,
    toggleSize,
    setSort,
    clearFilters,
    activeFilterCount,
  } = useProducts(products);

  // Gender counts for tabs
  const genderCounts = useMemo(() => {
    const counts: Record<string, number> = { men: 0, women: 0, unisex: 0 };
    products.forEach((p) => {
      counts[p.gender] = (counts[p.gender] || 0) + 1;
    });
    return counts;
  }, [products]);

  // Price range from data
  const priceRange = useMemo(() => {
    const prices = products.filter((p) => p.price !== null).map((p) => p.price!);
    return {
      min: 0,
      max: Math.ceil(Math.max(...prices) / 50) * 50,
    };
  }, [products]);

  return (
    <section id="catalog" className="relative px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto py-16 sm:py-20">
      {/* Section header */}
      <div className="text-center mb-12">
        <h2 className="font-serif text-2xl sm:text-3xl text-text-primary font-light tracking-wider">
          Our Collection
        </h2>
        <div className="mt-3 mx-auto flex items-center justify-center gap-3">
          <div className="h-px w-10 bg-gold/30" />
          <div className="w-1 h-1 rotate-45 bg-gold/40" />
          <div className="h-px w-10 bg-gold/30" />
        </div>
      </div>

      {/* Gender tabs */}
      <div className="flex justify-center mb-8 border-b border-white/[0.06]">
        <GenderTabs active={filters.gender} onChange={setGender} counts={genderCounts} />
      </div>

      {/* Search + Filter toggle + Sort */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-4">
        <div className="flex-1 max-w-md">
          <SearchBar value={filters.search} onChange={setSearch} />
        </div>

        <div className="flex items-center gap-2">
          {/* Mobile filter toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2.5 border rounded-md text-xs uppercase tracking-wider transition-all duration-300 ${
              showFilters || activeFilterCount > 0
                ? "border-gold/30 text-gold bg-gold/5"
                : "border-white/[0.06] text-text-tertiary hover:border-white/15"
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
            </svg>
            Filters
            {activeFilterCount > 0 && (
              <span className="w-5 h-5 flex items-center justify-center rounded-full bg-gold text-bg-primary text-[10px] font-semibold">
                {activeFilterCount}
              </span>
            )}
          </button>

          <SortDropdown value={filters.sort} onChange={setSort} />
        </div>
      </div>

      {/* Filter panel */}
      <div
        className={`overflow-hidden transition-all duration-400 ${
          showFilters ? "max-h-96 opacity-100 mb-6" : "max-h-0 opacity-0"
        }`}
      >
        <div className="p-4 sm:p-5 bg-bg-secondary/60 border border-white/[0.04] rounded-lg space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Brand */}
            <BrandFilter brands={brands} selected={filters.brand} onChange={setBrand} />

            {/* Price range */}
            <PriceRangeSlider
              min={priceRange.min}
              max={priceRange.max}
              value={filters.priceRange}
              onChange={setPriceRange}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Type chips */}
            <FilterChips
              label="Fragrance Type"
              options={FRAG_TYPES}
              selected={filters.types}
              onToggle={toggleType}
            />

            {/* Size chips */}
            <FilterChips
              label="Size"
              options={COMMON_SIZES}
              selected={filters.sizes}
              onToggle={toggleSize}
            />
          </div>
        </div>
      </div>

      {/* Active filters */}
      <div className="mb-4">
        <ActiveFilters
          filters={filters}
          onClearAll={clearFilters}
          onRemoveGender={() => setGender("all")}
          onRemoveBrand={() => setBrand(null)}
          onRemoveType={toggleType}
          onRemoveSize={toggleSize}
          onResetPrice={() => setPriceRange([0, 1000])}
        />
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between mb-6">
        <p className="text-text-tertiary text-xs sm:text-sm">
          Showing{" "}
          <span className="text-text-secondary tabular-nums">{filteredProducts.length}</span> of{" "}
          <span className="text-text-secondary tabular-nums">{products.length}</span> fragrances
        </p>
      </div>

      {/* Product grid */}
      <ProductGrid products={filteredProducts} onSelectProduct={setSelectedProduct} />

      {/* Product detail modal */}
      <ProductModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
    </section>
  );
}
