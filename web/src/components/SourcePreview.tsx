"use client";

import { useEffect, useRef, useState } from "react";
import { baseNameOf, cleanName, extensionOf, MAX_NAME_LENGTH } from "@/lib/audio";
import { formatBytes, formatTime } from "@/lib/format";
import { T } from "@/lib/teks";
import { useAudioPlayer } from "@/lib/useAudioPlayer";
import { AudioPlayer } from "./AudioPlayer";
import { Chip } from "./Chip";
import { Icon } from "./Icon";

export type SourceOrigin = "upload" | "record";

const MENU_ITEM =
  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[0.88rem] font-bold transition hover:bg-surface-2";

/** Pratinjau audio yang akan diproses: nama (bisa diganti), info singkat, pemutar, dan menu hapus.
 * Pemutar hanya untuk melihat dan mendengar; tidak ada transkrip di sini. */
export function SourcePreview({
  file,
  origin,
  previewUrl,
  durationSec,
  busy = false,
  onRename,
  onRemove,
}: {
  file: File;
  origin: SourceOrigin;
  previewUrl: string;
  durationSec: number | null;
  busy?: boolean; // sedang mengirim: ganti nama dan hapus dikunci
  onRename: (newName: string) => void;
  onRemove: () => void;
}) {
  const player = useAudioPlayer(previewUrl, durationSec ?? 0);
  const recorded = origin === "record";
  const duration = player.duration > 0 ? player.duration : durationSec;
  const extension = extensionOf(file.name);

  const [menuOpen, setMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);

  // Menu tertutup bila klik di luar atau menekan Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenuOpen(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  function startRename() {
    setDraft(baseNameOf(file.name));
    setNameError(null);
    setMenuOpen(false);
    setRenaming(true);
  }

  function cancelRename() {
    setRenaming(false);
    setNameError(null);
  }

  function saveRename() {
    const name = cleanName(draft);
    if (!name) return setNameError(T.audio.errEmptyName);
    if (name.length > MAX_NAME_LENGTH) return setNameError(T.audio.errNameTooLong(MAX_NAME_LENGTH));
    setRenaming(false);
    setNameError(null);
    const full = extension ? `${name}.${extension}` : name; // ekstensi tetap: format audionya tidak berubah
    if (full !== file.name) onRename(full);
  }

  return (
    <div>
      <div className="flex items-center gap-3 rounded-xl bg-good-soft px-3.5 py-2 text-[0.9rem] font-bold text-good">
        <Icon name="check" />

        {renaming ? (
          <form
            className="flex min-w-0 flex-1 items-center gap-1.5"
            onSubmit={(e) => {
              e.preventDefault();
              saveRename();
            }}
          >
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onFocus={(e) => e.target.select()}
              onKeyDown={(e) => {
                if (e.key === "Escape") cancelRename();
              }}
              aria-label={T.audio.nameLabel}
              aria-invalid={nameError !== null}
              className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-2.5 py-1.5 font-semibold text-ink outline-none focus:border-brand focus:ring-[3px] focus:ring-brand/25"
            />
            {extension && <span className="shrink-0 text-muted">.{extension}</span>}
            <button
              type="submit"
              aria-label={T.audio.saveName}
              title={T.audio.saveName}
              className="grid size-8 shrink-0 place-items-center rounded-lg bg-brand text-brand-fg transition hover:brightness-105"
            >
              <Icon name="check" />
            </button>
            <button
              type="button"
              onClick={cancelRename}
              aria-label={T.audio.cancelRename}
              title={T.audio.cancelRename}
              className="grid size-8 shrink-0 place-items-center rounded-lg transition hover:bg-surface"
            >
              <Icon name="x" />
            </button>
          </form>
        ) : (
          <>
            <span className="min-w-0 truncate">{file.name}</span>
            <div ref={menuRef} className="relative ml-auto">
              <button
                ref={menuButton}
                type="button"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                aria-label={T.audio.menu}
                title={T.audio.menu}
                disabled={busy}
                onClick={() => setMenuOpen((v) => !v)}
                className="grid size-8 shrink-0 place-items-center rounded-lg transition hover:bg-surface disabled:pointer-events-none disabled:opacity-40"
              >
                <Icon name="more" className="text-[1.3em]" />
              </button>
              {menuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-full z-30 mt-1.5 w-44 rounded-xl border border-line bg-surface p-1.5 text-ink shadow-card"
                >
                  <button type="button" role="menuitem" onClick={startRename} className={MENU_ITEM}>
                    <Icon name="pencil" />
                    {T.audio.rename}
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      onRemove();
                    }}
                    className={`${MENU_ITEM} text-bad hover:bg-bad-soft`}
                  >
                    <Icon name="trash" />
                    {T.audio.remove}
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {nameError && (
        <p role="alert" className="mt-1.5 text-[0.82rem] font-semibold text-bad">
          {nameError}
        </p>
      )}

      <div className="mb-3.5 mt-3 flex flex-wrap gap-2">
        <Chip tone="brand">
          <Icon name={recorded ? "mic" : "upload"} />
          {recorded ? T.audio.sourceRecording : T.audio.sourceUpload}
        </Chip>
        {duration !== null && duration > 0 && (
          <Chip>
            <Icon name="clock" />
            {formatTime(duration)}
          </Chip>
        )}
        <Chip>{formatBytes(file.size)}</Chip>
        {extension && <Chip>{extension.toUpperCase()}</Chip>}
      </div>

      <AudioPlayer player={player} />
    </div>
  );
}
