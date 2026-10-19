"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

/** Pesan singkat di bawah layar. Pakai: const { show, toast } = useToast(); render {toast}; panggil show("..."). */
export function useToast(): { show: (message: string) => void; toast: ReactNode } {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const show = useCallback((text: string) => {
    setMessage(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMessage(null), 2400);
  }, []);

  useEffect(() => () => clearTimeout(timer.current), []);

  const toast = (
    <div
      role="status"
      aria-live="polite"
      className={`pointer-events-none fixed bottom-6 left-1/2 z-[100] -translate-x-1/2 rounded-xl bg-ink px-[18px] py-3 text-[0.88rem] font-bold text-bg shadow-card transition duration-200 ${
        message ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      {message}
    </div>
  );

  return { show, toast };
}
