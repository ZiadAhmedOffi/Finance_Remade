/**
 * DPoP (Demonstration of Proof-of-Possession) Utilities
 * Implements client-side key generation and proof creation for RFC 9449.
 */

const KEY_ALGO = {
  name: "ECDSA",
  namedCurve: "P-256",
};

/**
 * Generates or retrieves a persistent DPoP key pair.
 * In a real application, this should be stored in IndexedDB.
 * For this implementation, we'll use a simple memory cache during session.
 */
let dpopKeyPair: CryptoKeyPair | null = null;

export const getDPoPKeyPair = async (): Promise<CryptoKeyPair> => {
  if (dpopKeyPair) return dpopKeyPair;
  
  dpopKeyPair = await window.crypto.subtle.generateKey(
    KEY_ALGO,
    false, // extractable
    ["sign", "verify"]
  );
  
  return dpopKeyPair;
};

/**
 * Exports a public key as JWK.
 */
export const exportJWK = async (key: CryptoKey): Promise<JsonWebKey> => {
  return await window.crypto.subtle.exportKey("jwk", key);
};

/**
 * Generates a DPoP proof (JWT).
 */
export const createDPoPProof = async (method: string, url: string): Promise<string> => {
  const keyPair = await getDPoPKeyPair();
  const publicJwk = await exportJWK(keyPair.publicKey);
  
  // Standard DPoP Header
  const header = {
    typ: "dpop+jwt",
    alg: "ES256",
    jwk: publicJwk,
  };
  
  // Standard DPoP Payload
  const payload = {
    jti: window.crypto.randomUUID(),
    htm: method.toUpperCase(),
    htu: url.includes('://') ? url.split('?')[0] : `${window.location.origin}${url.split('?')[0]}`,
    iat: Math.floor(Date.now() / 1000),
  };
  
  const encodedHeader = btoa(JSON.stringify(header)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const encodedPayload = btoa(JSON.stringify(payload)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  
  const dataToSign = new TextEncoder().encode(`${encodedHeader}.${encodedPayload}`);
  const signature = await window.crypto.subtle.sign(
    { name: "ECDSA", hash: { name: "SHA-256" } },
    keyPair.privateKey,
    dataToSign
  );
  
  const encodedSignature = btoa(String.fromCharCode(...new Uint8Array(signature)))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
    
  return `${encodedHeader}.${encodedPayload}.${encodedSignature}`;
};

/**
 * Computes JWK Thumbprint (SHA-256) of the public key.
 * Used for binding the token to the key (cnf claim).
 */
export const getJWKThumbprint = async (jwk: JsonWebKey): Promise<string> => {
  // RFC 7638 requires lexicographical order for thumbprint
  // For EC keys: crv, kty, x, y
  const required: any = {
    crv: jwk.crv,
    kty: jwk.kty,
    x: jwk.x,
    y: jwk.y,
  };
  
  // JSON.stringify will use the order of keys we defined above, 
  // which is already sorted: c, k, x, y.
  const json = JSON.stringify(required);
  const hash = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(json));
  
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
};
