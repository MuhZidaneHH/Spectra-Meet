import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SpectraMeet",
  description: "Ubah rekaman meeting jadi transkrip per pembicara dan ringkasan.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
