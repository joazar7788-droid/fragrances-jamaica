import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { WhatsAppFloat } from "@/components/layout/WhatsAppFloat";
import { HeroSection } from "@/components/hero/HeroSection";
import { CatalogSection } from "@/components/catalog/CatalogSection";
import productsData from "../../data/products.json";
import brandsData from "../../data/brands.json";
import { Product, Brand } from "@/types/product";

export default function HomePage() {
  const products = productsData as Product[];
  const brands = brandsData as Brand[];

  return (
    <>
      <Header />
      <main>
        <HeroSection />
        <CatalogSection products={products} brands={brands} />
      </main>
      <Footer />
      <WhatsAppFloat />
    </>
  );
}
