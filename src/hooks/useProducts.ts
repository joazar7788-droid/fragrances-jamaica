"use client";

import { useState, useMemo, useCallback } from "react";
import Fuse from "fuse.js";
import { Product, FilterState, Gender, SortOption } from "@/types/product";
import { useDebounce } from "./useDebounce";

const DEFAULT_FILTERS: FilterState = {
  gender: "all",
  search: "",
  brand: null,
  priceRange: [0, 1000],
  types: [],
  sizes: [],
  sort: "brand-asc",
};

function sortProducts(products: Product[], sort: SortOption): Product[] {
  const sorted = [...products];
  switch (sort) {
    case "name-asc":
      return sorted.sort((a, b) => a.name.localeCompare(b.name));
    case "name-desc":
      return sorted.sort((a, b) => b.name.localeCompare(a.name));
    case "price-asc":
      return sorted.sort((a, b) => (a.price ?? 9999) - (b.price ?? 9999));
    case "price-desc":
      return sorted.sort((a, b) => (b.price ?? 0) - (a.price ?? 0));
    case "brand-asc":
      return sorted.sort((a, b) => a.brand.localeCompare(b.brand) || a.name.localeCompare(b.name));
    default:
      return sorted;
  }
}

export function useProducts(allProducts: Product[]) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const debouncedSearch = useDebounce(filters.search, 200);

  // Fuse.js search index
  const searchIndex = useMemo(
    () =>
      new Fuse(allProducts, {
        keys: [
          { name: "name", weight: 0.35 },
          { name: "brand", weight: 0.35 },
          { name: "raw_name", weight: 0.3 },
        ],
        threshold: 0.35,
        ignoreLocation: true,
      }),
    [allProducts]
  );

  // Memoized filtering pipeline
  const filteredProducts = useMemo(() => {
    let results = allProducts;

    // 1. Gender filter
    if (filters.gender !== "all") {
      results = results.filter((p) => p.gender === filters.gender);
    }

    // 2. Fuzzy search
    if (debouncedSearch.length >= 2) {
      const searchResults = searchIndex.search(debouncedSearch);
      const searchIds = new Set(searchResults.map((r) => r.item.id));
      results = results.filter((p) => searchIds.has(p.id));
    }

    // 3. Brand filter
    if (filters.brand) {
      results = results.filter((p) => p.brand === filters.brand);
    }

    // 4. Type filter
    if (filters.types.length > 0) {
      results = results.filter((p) => p.type && filters.types.includes(p.type));
    }

    // 5. Size filter
    if (filters.sizes.length > 0) {
      results = results.filter((p) => p.size && filters.sizes.includes(p.size));
    }

    // 6. Price range
    results = results.filter((p) => {
      if (p.price === null) return true;
      return p.price >= filters.priceRange[0] && p.price <= filters.priceRange[1];
    });

    // 7. Sort
    results = sortProducts(results, filters.sort);

    return results;
  }, [allProducts, filters.gender, debouncedSearch, filters.brand, filters.types, filters.sizes, filters.priceRange, filters.sort, searchIndex]);

  const setGender = useCallback((gender: Gender) => {
    setFilters((prev) => ({ ...prev, gender }));
  }, []);

  const setSearch = useCallback((search: string) => {
    setFilters((prev) => ({ ...prev, search }));
  }, []);

  const setBrand = useCallback((brand: string | null) => {
    setFilters((prev) => ({ ...prev, brand }));
  }, []);

  const setPriceRange = useCallback((priceRange: [number, number]) => {
    setFilters((prev) => ({ ...prev, priceRange }));
  }, []);

  const toggleType = useCallback((type: string) => {
    setFilters((prev) => ({
      ...prev,
      types: prev.types.includes(type)
        ? prev.types.filter((t) => t !== type)
        : [...prev.types, type],
    }));
  }, []);

  const toggleSize = useCallback((size: string) => {
    setFilters((prev) => ({
      ...prev,
      sizes: prev.sizes.includes(size)
        ? prev.sizes.filter((s) => s !== size)
        : [...prev.sizes, size],
    }));
  }, []);

  const setSort = useCallback((sort: SortOption) => {
    setFilters((prev) => ({ ...prev, sort }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.gender !== "all") count++;
    if (filters.search.length >= 2) count++;
    if (filters.brand) count++;
    if (filters.types.length > 0) count += filters.types.length;
    if (filters.sizes.length > 0) count += filters.sizes.length;
    if (filters.priceRange[0] > 0 || filters.priceRange[1] < 1000) count++;
    return count;
  }, [filters]);

  return {
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
  };
}
