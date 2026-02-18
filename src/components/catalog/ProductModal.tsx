"use client";

import { useEffect, useCallback } from "react";
import { Product } from "@/types/product";
import { buildProductInquiryUrl } from "@/lib/whatsapp";
import { ProductPlaceholder } from "./ProductPlaceholder";

interface ProductModalProps {
  product: Product | null;
  onClose: () => void;
}

export function ProductModal({ product, onClose }: ProductModalProps) {
  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (product) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [product, handleKeyDown]);

  if (!product) return null;

  const inquiryUrl = buildProductInquiryUrl(product);
  const showImage = product.image_url && product.has_image;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4 sm:p-6"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-fade-in" />

      {/* Modal content */}
      <div
        className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-bg-secondary border border-white/[0.06] rounded-xl shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-bg-primary/80 border border-white/[0.08] text-text-tertiary hover:text-text-primary hover:border-gold/30 transition-all"
          aria-label="Close"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="flex flex-col sm:flex-row">
          {/* Image — larger view */}
          <div className="relative w-full sm:w-1/2 aspect-[3/4] sm:aspect-auto sm:min-h-[420px] bg-bg-primary shrink-0 overflow-hidden rounded-t-xl sm:rounded-l-xl sm:rounded-tr-none">
            {showImage ? (
              <img
                src={product.image_url!}
                alt={`${product.brand} ${product.name}`}
                className="w-full h-full object-contain p-4"
              />
            ) : (
              <ProductPlaceholder brand={product.brand} />
            )}

            {/* Gift set / Tester badge */}
            {product.is_gift_set && (
              <span className="absolute top-3 left-3 px-2.5 py-1 bg-gold/90 text-bg-primary text-[10px] uppercase tracking-wider font-medium rounded-sm">
                Gift Set
              </span>
            )}
            {product.is_tester && (
              <span className="absolute top-3 left-3 px-2.5 py-1 bg-bg-elevated/90 text-text-secondary text-[10px] uppercase tracking-wider font-medium rounded-sm border border-white/10">
                Tester
              </span>
            )}
          </div>

          {/* Product details */}
          <div className="flex-1 p-6 sm:p-8 flex flex-col justify-center">
            {/* Brand */}
            <p className="text-gold/80 text-[11px] uppercase tracking-[0.2em] font-medium">
              {product.brand}
            </p>

            {/* Product name */}
            <h2 className="mt-2 text-text-primary text-xl sm:text-2xl font-serif font-light leading-snug">
              {product.name}
            </h2>

            {/* Decorative divider */}
            <div className="mt-4 mb-4 w-8 h-px bg-gold/30" />

            {/* Details grid */}
            <div className="space-y-3">
              {product.type && (
                <div className="flex items-center justify-between">
                  <span className="text-text-tertiary text-xs uppercase tracking-wider">Type</span>
                  <span className="text-text-secondary text-sm">{product.type}</span>
                </div>
              )}
              {product.size && (
                <div className="flex items-center justify-between">
                  <span className="text-text-tertiary text-xs uppercase tracking-wider">Size</span>
                  <span className="text-text-secondary text-sm">{product.size}</span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-text-tertiary text-xs uppercase tracking-wider">For</span>
                <span className="text-text-secondary text-sm capitalize">{product.gender}</span>
              </div>
            </div>

            {/* Price */}
            <div className="mt-6 pt-4 border-t border-white/[0.06]">
              {product.price ? (
                <div className="flex items-baseline gap-1">
                  <span className="text-text-primary text-3xl font-light tabular-nums">
                    ${product.price.toFixed(2)}
                  </span>
                  <span className="text-text-tertiary text-xs uppercase tracking-wider ml-1">USD</span>
                </div>
              ) : (
                <span className="text-gold/70 text-sm uppercase tracking-wider">
                  Contact for Price
                </span>
              )}
            </div>

            {/* WhatsApp inquiry button */}
            <a
              href={inquiryUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-6 w-full flex items-center justify-center gap-2.5 px-5 py-3 bg-gold text-bg-primary text-sm uppercase tracking-[0.12em] font-medium rounded-md transition-all duration-300 hover:bg-gold-light hover:shadow-[0_4px_20px_rgba(201,169,110,0.3)]"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
              </svg>
              Inquire on WhatsApp
            </a>

            {/* Full product name for reference */}
            <p className="mt-4 text-text-tertiary/50 text-[10px] tracking-wider truncate">
              {product.raw_name}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
