// Signed session cookie shared by middleware (edge runtime) and the login route; Web Crypto works in both.
export const SESSION_COOKIE = "admind_session";
export const SESSION_DAYS = 14;

const enc = new TextEncoder();

async function sign(data: string): Promise<string> {
  const secret = (process.env.ENGINE_TOKEN_SECRET || "") + "|" + (process.env.APP_PASSWORD || "");
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, [
    "sign",
  ]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(data)));
  return btoa(String.fromCharCode(...sig)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
}

export async function createSession(): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + SESSION_DAYS * 86400;
  return `${exp}.${await sign(String(exp))}`;
}

export async function validSession(value: string | undefined): Promise<boolean> {
  if (!value || !value.includes(".")) return false;
  const [exp, sig] = value.split(".", 2);
  if (Number(exp) < Date.now() / 1000) return false;
  return (await sign(exp)) === sig;
}
