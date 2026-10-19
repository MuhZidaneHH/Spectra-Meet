import { formatTime } from "./format";
import { T } from "./teks";
import type { Segment, SpeakerInfo } from "./types";

/** Cara satu pembicara ditampilkan: nama dan warna. */
export type SpeakerStyle = { name: string; color: string };

// Token warna pembicara (globals.css). Bila pembicara lebih dari tiga, warnanya berulang.
const COLORS = ["var(--sp-0)", "var(--sp-1)", "var(--sp-2)"];
const UNKNOWN: SpeakerStyle = { name: T.result.unknownSpeaker, color: "var(--muted)" };

/** Nama dan warna tiap pembicara.
 * Kontrak: `segments[].speaker` berupa ID stabil (SPEAKER_00), dan nama tampilannya ada di `speakers[]`.
 * ID di segmen yang tidak ada di daftar tetap ditampilkan ("Pembicara N" menurut urutan muncul),
 * dan segmen tanpa pembicara ditampilkan sebagai "Tidak diketahui". */
export function mapSpeakers(segments: Segment[], speakers: SpeakerInfo[] = []) {
  const byId = new Map<string, SpeakerStyle>();
  const add = (id: string, label?: string) => {
    const n = byId.size;
    byId.set(id, { name: label?.trim() || T.result.speaker(n + 1), color: COLORS[n % COLORS.length] });
  };
  speakers.forEach((s) => add(s.id, s.label));
  for (const s of segments) if (s.speaker && !byId.has(s.speaker)) add(s.speaker);

  // Hanya yang benar-benar bicara yang masuk legenda dan hitungan.
  const spoke = new Set(segments.map((s) => s.speaker).filter((id): id is string => !!id));
  const list = [...byId.entries()].filter(([id]) => spoke.has(id)).map(([, style]) => style);

  const styleOf = (id: string | null | undefined): SpeakerStyle => (id && byId.get(id)) || UNKNOWN;
  return { list, styleOf };
}

/** Teks transkrip untuk disalin: "[mm:ss] Pembicara 1: kalimat". */
export function transcriptAsText(segments: Segment[], styleOf: (id: string | null | undefined) => SpeakerStyle): string {
  return segments.map((s) => `[${formatTime(s.start)}] ${styleOf(s.speaker).name}: ${s.text}`).join("\n");
}
