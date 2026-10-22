import {
  DEFAULT_LOGIN_REDIRECT,
  LOGIN_REDIRECT_DECODE_ROUNDS,
  LOGIN_REDIRECT_PARSE_ORIGIN,
} from "@/constants/auth";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

const PATH_SEPARATOR = "/";
const SCHEME_RELATIVE_PREFIX = "//";
const BACKSLASH = "\\";
const CONTROL_CHAR = /[\u0000-\u001f\u007f]/;

/** A path that a browser could read as another host or that hides one. */
function hasUnsafeShape(path: string): boolean {
  return (
    !path.startsWith(PATH_SEPARATOR) ||
    path.startsWith(SCHEME_RELATIVE_PREFIX) ||
    path.includes(BACKSLASH) ||
    CONTROL_CHAR.test(path)
  );
}

/** Every percent-decoding of `value` (up to the round limit), or null when malformed. */
function decodedForms(value: string): string[] | null {
  const forms = [value];
  let current = value;
  for (let round = 0; round < LOGIN_REDIRECT_DECODE_ROUNDS; round++) {
    try {
      current = decodeURIComponent(current);
    } catch {
      return null;
    }
    forms.push(current);
  }
  return forms;
}

/** The path, query and hash of `value` when it parses to the placeholder origin. */
function sameOriginTarget(value: string): string | null {
  const parsed = new URL(value, LOGIN_REDIRECT_PARSE_ORIGIN);
  if (parsed.origin !== LOGIN_REDIRECT_PARSE_ORIGIN) {
    return null;
  }
  return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

function isLoginPage(target: string): boolean {
  return target.startsWith(PUBLIC_ROUTE_PATHS.LOGIN);
}

/**
 * The post-login return path when it is a same-origin page, else the default.
 *
 * Rejects absolute and scheme-relative URLs, backslashes, control characters
 * (tab, newline, NUL), also when hidden behind percent-encoding (``/%5Chost``,
 * ``/%2F%2Fhost``), malformed encodings, and the login page itself.
 */
export function sanitizeLoginRedirect(redirect: string | null): string {
  const forms = redirect ? decodedForms(redirect) : null;
  if (!redirect || !forms || forms.some(hasUnsafeShape)) {
    return DEFAULT_LOGIN_REDIRECT;
  }
  const target = sameOriginTarget(redirect);
  if (!target || isLoginPage(target)) {
    return DEFAULT_LOGIN_REDIRECT;
  }
  return target;
}
