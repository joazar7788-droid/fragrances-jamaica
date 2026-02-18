/**
 * Generates deterministic placeholder styling for products without images.
 * All products from the same brand get a consistent visual treatment.
 */

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return Math.abs(hash);
}

export function getBrandInitials(brand: string): string {
  const words = brand.replace(/[^a-zA-Z0-9\s]/g, "").split(/\s+/);
  if (words.length === 1) {
    return words[0].substring(0, 2).toUpperCase();
  }
  return words
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

export function getBrandGradient(brand: string): string {
  const hash = hashString(brand);
  const hue = hash % 360;
  // Low saturation, very dark — luxury feel
  return `linear-gradient(135deg, hsl(${hue}, 12%, 11%), hsl(${(hue + 40) % 360}, 16%, 7%))`;
}

export function getBrandAccentColor(brand: string): string {
  const hash = hashString(brand);
  const hue = hash % 360;
  return `hsl(${hue}, 20%, 30%)`;
}
