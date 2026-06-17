// Re-export shim (AE-0156): canonical home is @/modules/identity.
export {
  setAccessTokenCookie,
  clearAccessTokenCookie,
  sanitizeLoginRedirect,
  isSecureRequest,
  COOKIE_ACCESS_TOKEN,
} from "@/modules/identity";
