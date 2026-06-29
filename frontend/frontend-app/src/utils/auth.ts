type JwtPayload = {
  exp?: number;
  roles?: Array<{
    role?: string;
    fund?: string | null;
    fund_id?: string | null;
    portfolio_id?: string | null;
  }>;
  [key: string]: unknown;
};

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

const getStorage = () => window.sessionStorage;

const decodeBase64Url = (value: string) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  return atob(padded);
};

export const getAccessToken = () => getStorage().getItem(ACCESS_TOKEN_KEY);

export const getRefreshToken = () => getStorage().getItem(REFRESH_TOKEN_KEY);

export const setAuthTokens = (accessToken: string, refreshToken: string) => {
  const storage = getStorage();
  storage.setItem(ACCESS_TOKEN_KEY, accessToken);
  storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
};

export const clearAuthTokens = () => {
  const storage = getStorage();
  storage.removeItem(ACCESS_TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
};

export const getTokenPayload = (): JwtPayload | null => {
  const token = getAccessToken();
  if (!token) return null;

  try {
    const [, payload] = token.split(".");
    return JSON.parse(decodeBase64Url(payload));
  } catch {
    return null;
  }
};

export const isAccessTokenValid = () => {
  const payload = getTokenPayload();
  if (!payload?.exp) return false;
  return payload.exp > Date.now() / 1000;
};

export const hasAnyRole = (roleNames: string[]) => {
  const roles = getTokenPayload()?.roles || [];
  return roles.some((role) => role.role && roleNames.includes(role.role));
};
