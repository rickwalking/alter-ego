import { verifyAccessToken } from "./jwt-auth";

const MS_PER_SECOND = 1000;

/** Whether ``token`` is a valid, unexpired access token. */
export async function isLiveSession(
  token: string | undefined,
): Promise<boolean> {
  if (!token) return false;
  const payload = await verifyAccessToken(token);
  return payload !== null && payload.exp * MS_PER_SECOND > Date.now();
}
