"use client";

import { useRef, useState } from "react";
import { T } from "@/lib/teks";
import { Icon } from "./Icon";

/** Kotak unggah file: klik, atau seret file ke dalamnya. Validasi dilakukan pemanggil. */
export function UploadBox({
  extensions,
  disabled,
  onFile,
}: {
  extensions: string[];
  disabled?: boolean;
  onFile: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  const pick = () => inputRef.current?.click();

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label={T.audio.uploadTitle}
      aria-disabled={disabled}
      onClick={() => !disabled && pick()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          pick();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const file = e.dataTransfer.files[0];
        if (file && !disabled) onFile(file);
      }}
      className={`grid cursor-pointer justify-items-center gap-1.5 rounded-2xl border-2 border-dashed px-4 py-8 text-center transition aria-disabled:cursor-not-allowed aria-disabled:opacity-50 ${
        over ? "border-brand bg-brand-soft" : "border-line bg-surface-2 hover:border-brand hover:bg-brand-soft"
      }`}
    >
      <span className="grid size-[54px] place-items-center rounded-2xl bg-surface text-2xl text-brand shadow-card">
        <Icon name="upload" />
      </span>
      <b className="text-base">{T.audio.uploadTitle}</b>
      <small className="text-muted">{T.audio.uploadHint(extensions.map((e) => e.toUpperCase()).join(", "))}</small>
      <input
        ref={inputRef}
        type="file"
        accept={extensions.map((e) => `.${e}`).join(",")}
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = ""; // agar file yang sama bisa dipilih ulang
        }}
      />
    </div>
  );
}
