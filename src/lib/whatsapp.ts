import { Product } from "@/types/product";

const WHATSAPP_NUMBER = "18764365300";

export function buildWhatsAppUrl(message: string): string {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}

export function buildProductInquiryUrl(product: Product): string {
  const lines = [
    `Hi! I'm interested in:`,
    ``,
    `*${product.brand} — ${product.name}*`,
  ];

  if (product.size) lines.push(`Size: ${product.size}`);
  if (product.type) lines.push(`Type: ${product.type}`);

  lines.push(
    `Listed Price: ${product.price ? `$${product.price.toFixed(2)}` : "Contact for price"}`
  );
  lines.push(``);
  lines.push(`Is this available? Please let me know the details.`);

  return buildWhatsAppUrl(lines.join("\n"));
}

export const DEFAULT_MESSAGE =
  "Hi! I'm interested in ordering from Fragrances Jamaica. Can you help me?";

export const DEFAULT_WHATSAPP_URL = buildWhatsAppUrl(DEFAULT_MESSAGE);
