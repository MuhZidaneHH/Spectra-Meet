// Konstanta tampilan yang tidak rahasia. Pengaturan yang bisa diubah pengguna
// (batas unggahan, format, interval polling, pilihan form) ada di .env dan
// datang lewat GET /api/config, bukan di sini.

export const APP_NAME = "SpectraMeet";

/** Kunci localStorage untuk tema pilihan pengguna. */
export const THEME_STORAGE_KEY = "sm-theme";

/** Seberapa sering status mesin di header diperbarui (milidetik). */
export const HEALTH_REFRESH_MS = 30_000;

/** Batas lama rekaman dari mikrofon (detik), agar file tidak membengkak. */
export const MAX_RECORD_SECONDS = 60 * 60;
