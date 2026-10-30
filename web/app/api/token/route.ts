import { createHmac } from "crypto";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const b64url = (buf: Buffer) => buf.toString("base64").replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");

// Mints a 2-hour token the browser uses to talk to the engine directly (see engine/app/auth.py).
export async function GET() {
  const secret = process.env.ENGINE_TOKEN_SECRET;
  const engineUrl = (process.env.ENGINE_URL || "http://localhost:8090").replace(/\/$/, "");
  if (!secret) return NextResponse.json({ engineUrl, token: "" });
  const payload = b64url(Buffer.from(JSON.stringify({ sub: "web", exp: Math.floor(Date.now() / 1000) + 7200 })));
  const sig = b64url(createHmac("sha256", secret).update(payload).digest());
  return NextResponse.json({ engineUrl, token: `${payload}.${sig}` });
}
