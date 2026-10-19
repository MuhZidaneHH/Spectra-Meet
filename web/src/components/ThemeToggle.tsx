"use client";

import { THEME_STORAGE_KEY } from "@/lib/config";
import { T } from "@/lib/teks";
import { Icon } from "./Icon";

function toggleTheme() {
  const root = document.documentElement;
  const current =
    root.getAttribute("data-theme") ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    /* penyimpanan diblokir: tema tetap berlaku untuk sesi ini */
  }
}

export function ThemeToggle() {
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={T.header.toggleTheme}
      title={T.header.toggleTheme}
      className="grid size-[38px] place-items-center rounded-[11px] border border-line bg-surface transition hover:bg-surface-2"
    >
      <Icon name="contrast" />
    </button>
  );
}
