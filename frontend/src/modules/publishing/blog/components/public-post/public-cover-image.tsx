"use client";

import { useState } from "react";
import Image from "next/image";
import type { PublicCoverImageProps } from "./types";

/**
 * AE-0412 (B08): a public cover image that removes itself — frame included —
 * when the image fails to load, so visitors never see a broken image.
 */
export function PublicCoverImage({
  src,
  alt,
  sizes,
  frameClassName,
  frameStyle,
  overlay,
}: PublicCoverImageProps): React.ReactElement | null {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return null;
  }
  return (
    <div className={frameClassName} style={frameStyle}>
      <Image
        src={src}
        alt={alt}
        fill
        sizes={sizes}
        className="object-cover"
        unoptimized
        onError={() => setFailed(true)}
      />
      {overlay}
    </div>
  );
}
