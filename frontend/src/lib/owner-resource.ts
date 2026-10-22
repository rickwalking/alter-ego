import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { resolveBackendUrl } from "@/constants/api";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HTTP_NOT_FOUND = 404;

/** What the backend says about an owner-only resource. */
export type OwnerResourceCheck = "found" | "missing" | "unknown";

/**
 * Ask the backend (server side, with the visitor's session cookie) whether the
 * resource at `apiPath` exists. Only a 404 counts as missing; auth errors,
 * server errors and an unreachable backend are "unknown" so the page keeps
 * its own login and error handling.
 */
export async function checkOwnerResource(
  apiPath: string,
): Promise<OwnerResourceCheck> {
  const cookieHeader = (await cookies()).toString();
  try {
    const response = await fetch(`${resolveBackendUrl()}${apiPath}`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    });
    if (response.ok) {
      return "found";
    }
    return response.status === HTTP_NOT_FOUND ? "missing" : "unknown";
  } catch {
    return "unknown";
  }
}

/**
 * Render the not-found page (HTTP 404) for a malformed id or a resource the
 * backend does not have, before the client page streams.
 */
export async function notFoundUnlessOwnerResource(
  id: string,
  apiPathFor: (id: string) => string,
): Promise<void> {
  if (!UUID_PATTERN.test(id)) {
    notFound();
  }
  if ((await checkOwnerResource(apiPathFor(id))) === "missing") {
    notFound();
  }
}
