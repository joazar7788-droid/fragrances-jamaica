"use client";

import { useState } from "react";
import { Product } from "@/types/product";
import { buildProductInquiryUrl } from "@/lib/whatsapp";
import { ProductPlaceholder } from "./ProductPlaceholder";

interface ProductCardProps {
  product: Product;
  onSelect: (product: Product) => void;
}

export function ProductCard({ product, onSelect }: ProductCardProps) {
  const [imageError, setImageError] = useState(false);
  const inquiryUrl = buildProductInquiryUrl(product);
  const showImage = product.image_url && !imageError;

  return (
    <div
      className="group relative bg-bg-secondary border border-white/[0.04] rounded-lg overflow-hidden transition-all duration-300 hover:border-gold/20 hover:shadow-[0_8px_40px_rgba(201,169,110,0.06)] hover:-translate-y-1 cursor-pointer"
      onClick={() => onSelect(product)}
    >
      {/* Image area */}
      <div className="relative aspect-[3/4] overflow-hidden bg-bg-primary">
        {showImage ? (
          <img
            src={product.image_url!}
            alt={`${product.brand} ${product.name}`}
            className="w-full h-full object-contain transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
            onError={() => setImageError(true)}
          />
        ) : (
          <ProductPlaceholder brand={product.brand} />
        )}

        {/* Gift set / Tester badge */}
        {product.is_gift_set && (
          <span className="absolute top-2 left-2 px-2 py-0.5 bg-gold/90 text-bg-primary text-[10px] uppercase tracking-wider font-medium rounded-sm">
            Gift Set
          </span>
        )}
        {product.is_tester && (
          <span className="absolute top-2 left-2 px-2 py-0.5 bg-bg-elevated/90 text-text-secondary text-[10px] uppercase tracking-wider font-medium rounded-sm border border-white/10">
            Tester
          </span>
        )}

        {/* Expand icon on hover */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/20 transition-all duration-300">
          <div className="w-10 h-10 rounded-full bg-bg-primary/80 border border-gold/30 flex items-center justify-center opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-300">
            <svg className="w-4 h-4 text-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
            </svg>
          </div>
        </div>
      </div>

      {/* Product info */}
      <div className="p-3 sm:p-4">
        {/* Brand */}
        <p className="text-gold/80 text-[10px] sm:text-[11px] uppercase tracking-[0.15em] font-medium truncate">
          {product.brand}
        </p>

        {/* Product name */}
        <h3 className="mt-1 text-text-primary text-sm sm:text-base font-light leading-snug line-clamp-2 min-h-[2.5em]">
          {product.name}
        </h3>

        {/* Type + Size badges */}
        <div className="mt-2 flex flex-wrap gap-1.5">
          {product.type && (
            <span className="px-2 py-0.5 bg-bg-tertiary/80 text-text-secondary text-[10px] uppercase tracking-wider rounded-sm">
              {product.type}
            </span>
          )}
          {product.size && (
            <span className="px-2 py-0.5 bg-bg-tertiary/80 text-text-secondary text-[10px] uppercase tracking-wider rounded-sm">
              {product.size}
            </span>
          )}
        </div>

        {/* Price */}
        <div className="mt-3">
          {product.price ? (
            <span className="text-text-primary text-lg sm:text-xl font-light tabular-nums">
              ${product.price.toFixed(2)}
            </span>
          ) : (
            <span className="text-gold/60 text-xs uppercase tracking-wider">
              Contact for Price
            </span>
          )}
        </div>

        {/* WhatsApp inquiry button */}
        <a
          href={inquiryUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-transparent border border-gold/25 text-gold/80 text-[11px] uppercase tracking-[0.12em] rounded-sm transition-all duration-300 hover:bg-gold hover:text-bg-primary hover:border-gold"
        >
          <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
          </svg>
          Inquire
        </a>
      </div>
    </div>
  );
}
