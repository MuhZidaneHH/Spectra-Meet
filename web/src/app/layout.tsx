import type { Metadata } from "next";
import localFont from "next/font/local";
import { Header } from "@/components/Header";
import { APP_NAME, THEME_STORAGE_KEY } from "@/lib/config";
import { T } from "@/lib/teks";
import "./globals.css";

// Plus Jakarta Sans (SIL OFL, lisensi di ./fonts/OFL.txt), disimpan di repo agar
// setup dan build tidak butuh internet. Variabel 200-800, subset latin (cukup untuk bahasa Indonesia).
const jakarta = localFont({
  src: "./fonts/PlusJakartaSans-latin.woff2",
  variable: "--font-jakarta",
  weight: "200 800",
  display: "swap",
});

export const metadata: Metadata = {
  title: APP_NAME,
  description: T.app.tagline,
};

// Menerapkan tema tersimpan sebelum halaman tampil, supaya tidak berkedip.
const themeScript = `try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id" className={`${jakarta.variable} h-full`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="flex min-h-full flex-col">
        <Header />
        <div className="mx-auto w-full max-w-5xl flex-1 px-4 pb-20 pt-6 sm:px-6">{children}</div>
      </body>
    </html>
  );
}
