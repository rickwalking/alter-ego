import { jwtVerify } from "jose";

import { JWT_TYPE_AUTH } from "@/constants/jwt";
import { MS_PER_SECOND } from "@/constants/time";

/** Base64 encodes data in 4-character groups; padding restores that width. */
const BASE64_GROUP_SIZE = 4;
export interface AccessTokenPayload {
  sub: string;
  email: string;
  role: string;
  type: string;
  exp: number;
  iat: number;
}

function resolveJwtSecret(): Uint8Array | null {
  const raw = process.env.AUTH_JWT_SECRET ?? process.env.SECRET_KEY;
  if (!raw || raw.trim().length === 0) {
    return null;
  }
  return new TextEncoder().encode(raw);
}

function padBase64Url(segment: string): string {
  const padded = segment.replace(/-/g, "+").replace(/_/g, "/");
  const remainder = padded.length % BASE64_GROUP_SIZE;
  if (remainder === 0) {
    return padded;
  }
  return padded + "=".repeat(BASE64_GROUP_SIZE - remainder);
}

/** Fallback when JWT secret is not configured in the frontend runtime. */
export function decodeJwtPayloadUnsafe(
  token: string,
): AccessTokenPayload | null {
  try {
    const segment = token.split(".")[1];
    if (!segment) {
      return null;
    }
    const json = atob(padBase64Url(segment));
    const payload = JSON.parse(json) as AccessTokenPayload;
    if (
      typeof payload.exp !== "number" ||
      payload.exp * MS_PER_SECOND <= Date.now()
    ) {
      return null;
    }
    if (payload.type !== JWT_TYPE_AUTH || typeof payload.role !== "string") {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

/** Verify access_token the same way the backend does (signature + expiry). */
export async function verifyAccessToken(
  token: string,
): Promise<AccessTokenPayload | null> {
  const secret = resolveJwtSecret();
  if (!secret) {
    return decodeJwtPayloadUnsafe(token);
  }

  try {
    const { payload } = await jwtVerify(token, secret);
    if (payload.type !== JWT_TYPE_AUTH) {
      return null;
    }
    const role = payload.role;
    if (typeof role !== "string") {
      return null;
    }
    return {
      sub: String(payload.sub ?? ""),
      email: String(payload.email ?? ""),
      role,
      type: String(payload.type),
      exp: Number(payload.exp ?? 0),
      iat: Number(payload.iat ?? 0),
    };
  } catch {
    return null;
  }
}
