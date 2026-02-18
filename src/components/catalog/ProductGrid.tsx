"use client";

import { useState, useEffect, useRef } from "react";
import { Product } from "@/types/product";
import { ProductCard } from "./ProductCard";

const BATCH_SIZE = 40;

interface ProductGridProps {
  products: Product[];
  onSelectProduct: (product: Product) => void;
}

export function ProductGrid({ products, onSelectProduct }: ProductGridProps) {
  const [visibleCount, setVisibleCount] = useState(BATCH_SIZE);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Reset when products change (new filter applied)
  useEffect(() => {
    setVisibleCount(BATCH_SIZE);
  }, [products]);

  // Intersection Observer for progressive loading
  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisibleCount((prev) => Math.min(prev + BATCH_SIZE, products.length));
        }
      },
      { rootMargin: "400px" }
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [products.length]);

  const visibleProducts = products.slice(0, visibleCount);

  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-16 h-16 mb-6 border border-gold/20 rounded-full flex items-center justify-center">
          <svg className="w-7 h-7 text-gold/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <p className="text-text-secondary text-lg font-light">No fragrances found</p>
        <p className="text-text-tertiary text-sm mt-2">Try adjusting your filters</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-5">
        {visibleProducts.map((product) => (
          <ProductCard key={product.id} product={product} onSelect={onSelectProduct} />
        ))}
      </div>

      {visibleCount < products.length && (
        <div ref={loadMoreRef} className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-gold/40 animate-pulse" />
            <span className="text-text-tertiary text-xs tracking-wider uppercase">
              Loading more
            </span>
            <div className="w-1.5 h-1.5 rounded-full bg-gold/40 animate-pulse" style={{ animationDelay: "150ms" }} />
          </div>
        </div>
      )}
    </>
  );
}
