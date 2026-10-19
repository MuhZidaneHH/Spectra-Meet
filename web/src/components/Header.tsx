import Link from "next/link";
import { APP_NAME } from "@/lib/config";
import { T } from "@/lib/teks";
import { EngineStatus } from "./EngineStatus";
import { ThemeToggle } from "./ThemeToggle";

const BAR_HEIGHTS = [10, 20, 28, 16, 22, 9];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 text-lg font-extrabold tracking-tight">
      <span className="flex h-7 items-center gap-[2.5px]" aria-hidden="true">
        {BAR_HEIGHTS.map((h, i) => (
          <b key={i} className="w-1 rounded-[3px] bg-gradient-to-b from-brand to-cyan" style={{ height: h }} />
        ))}
      </span>
      {APP_NAME}
    </Link>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Logo />
          <nav aria-label="Navigasi utama">
            <Link
              href="/"
              className="rounded-lg px-3 py-1.5 text-sm font-bold text-muted transition hover:bg-surface-2 hover:text-ink"
            >
              {T.header.newAudio}
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <EngineStatus />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
