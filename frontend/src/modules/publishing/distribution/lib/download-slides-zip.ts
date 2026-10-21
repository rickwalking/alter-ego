/**
 * AE-0446: "download all" for the publish carousel viewer, moved out of the
 * component unchanged — fetch every slide (30 s timeout each, failures
 * skipped), zip them and hand the archive to the browser.
 */
import JSZip from "jszip";

const FETCH_TIMEOUT_MS = 30000;
const DEFAULT_ARCHIVE_NAME = "slides";
const WHITESPACE = /\s+/g;

function archiveName(alt: string): string {
  return alt.replace(WHITESPACE, "_") || DEFAULT_ARCHIVE_NAME;
}

async function addSlide(
  folder: JSZip,
  url: string,
  index: number,
): Promise<void> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      credentials: "include",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    folder.file(`slide_${index + 1}.jpg`, await response.blob());
  } catch {
    // Ignore individual fetch failures
  } finally {
    clearTimeout(timeoutId);
  }
}

function saveBlob(content: Blob, fileName: string): void {
  const downloadUrl = window.URL.createObjectURL(content);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}

/** Zip every slide image and download it as ``<alt>.zip``. */
export async function downloadSlidesZip(
  slideUrls: readonly string[],
  alt: string,
): Promise<void> {
  const zip = new JSZip();
  const folder = zip.folder(archiveName(alt));
  if (!folder) return;
  await Promise.all(slideUrls.map((url, i) => addSlide(folder, url, i)));
  const content = await zip.generateAsync({ type: "blob" });
  saveBlob(content, `${archiveName(alt)}.zip`);
}
