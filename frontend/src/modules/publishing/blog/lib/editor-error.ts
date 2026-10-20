/**
 * Error-copy mapping of the blog editor (AE-0438, F-11).
 *
 * A failed editor action carries a typed kind plus the backend `detail` code.
 * The copy key picks the code-specific message when the backend code is known
 * (self-review, empty version, image budget, rewrite limits, ...) and falls
 * back to the kind-level message (422 validation, 409 conflict, 5xx).
 */

import { BLOG_EDITOR_ERROR_CODE_KEYS } from "@/constants/blog-editor";
import type { BlogEditorError } from "../types";

export function editorErrorKey(error: BlogEditorError): string {
  const code = error.detail
    ? BLOG_EDITOR_ERROR_CODE_KEYS[
        error.detail as keyof typeof BLOG_EDITOR_ERROR_CODE_KEYS
      ]
    : undefined;
  return code ? `errors.code.${code}` : `errors.${error.kind}`;
}
