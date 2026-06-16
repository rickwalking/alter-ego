// Re-export shim (AE-0156): canonical home is @/modules/identity.
export { verifyAccessToken, decodeJwtPayloadUnsafe } from "@/modules/identity";
export type { AccessTokenPayload } from "@/modules/identity";
