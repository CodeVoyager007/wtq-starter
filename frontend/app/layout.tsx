import type { Metadata } from "next";
import "@fontsource/dancing-script/600.css";
import "@fontsource/dancing-script/700.css";
import "@fontsource/tinos/400.css";
import "@fontsource/tinos/400-italic.css";
import "@fontsource/tinos/700.css";
import "@fontsource-variable/inter";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { siteConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: siteConfig.name,
  description: siteConfig.tagline,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
