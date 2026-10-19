/** Membaca durasi file audio di browser. Mengembalikan null bila tidak terbaca
 * (mis. rekaman webm tanpa durasi di header). */
export function readDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    const finish = (value: number | null) => {
      clearTimeout(timer);
      URL.revokeObjectURL(url);
      resolve(value);
    };
    const timer = setTimeout(() => finish(null), 4000);
    audio.preload = "metadata";
    audio.onloadedmetadata = () => finish(Number.isFinite(audio.duration) ? audio.duration : null);
    audio.onerror = () => finish(null);
    audio.src = url;
  });
}

export function extensionOf(filename: string): string {
  const i = filename.lastIndexOf(".");
  return i < 0 ? "" : filename.slice(i + 1).toLowerCase();
}

/** Nama tanpa ekstensi: "rapat.final.m4a" -> "rapat.final". */
export function baseNameOf(filename: string): string {
  const i = filename.lastIndexOf(".");
  return i <= 0 ? filename : filename.slice(0, i);
}

export const MAX_NAME_LENGTH = 80;

/** Membersihkan nama yang diketik pengguna: buang karakter terlarang di nama file dan rapikan spasi. */
export function cleanName(raw: string): string {
  return raw
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
