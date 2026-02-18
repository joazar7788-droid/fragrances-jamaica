export interface Product {
  id: string;
  raw_name: string;
  brand: string;
  name: string;
  size: string | null;
  type: string | null;
  gender: "men" | "women" | "unisex";
  price: number | null;
  upc: string;
  is_gift_set: boolean;
  is_tester: boolean;
  image_url: string | null;
  has_image: boolean;
}

export interface Brand {
  name: string;
  count: number;
}

export interface CatalogStats {
  total_products: number;
  by_gender: Record<string, number>;
  by_type: Record<string, number>;
  by_size: Record<string, number>;
  price_range: {
    min: number;
    max: number;
    avg: number;
  };
  missing_prices: number;
  gift_sets: number;
  testers: number;
  with_images: number;
}

export type Gender = "all" | "men" | "women" | "unisex";
export type SortOption = "name-asc" | "name-desc" | "price-asc" | "price-desc" | "brand-asc";

export interface FilterState {
  gender: Gender;
  search: string;
  brand: string | null;
  priceRange: [number, number];
  types: string[];
  sizes: string[];
  sort: SortOption;
}
