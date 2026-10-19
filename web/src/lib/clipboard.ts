/** Menyalin teks ke clipboard. Mengembalikan false bila gagal.
 * Clipboard API hanya ada di konteks aman (localhost/HTTPS) dan butuh izin; bila tidak
 * tersedia, dicoba cara lama lewat textarea tersembunyi (tetap harus dari klik pengguna). */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    /* lanjut ke cara cadangan */
  }

  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.cssText = "position:fixed;top:0;left:0;opacity:0;pointer-events:none";
  document.body.appendChild(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}
