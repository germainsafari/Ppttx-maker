"use client";

import { FormEvent, useState } from "react";

export default function Login() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setBusy(false);
    if (!r.ok) return setError("Wrong password. Ask the Admind team for access.");
    const next = new URLSearchParams(window.location.search).get("next");
    window.location.href = next && next.startsWith("/") ? next : "/";
  }

  return (
    <main className="wrap" style={{ maxWidth: 520, paddingTop: 120 }}>
      <div className="eyebrow">Admind deck builder</div>
      <h1 className="us">Sign in</h1>
      <p className="lead">Enter the team password to create presentations.</p>
      <form className="card" onSubmit={submit}>
        <label htmlFor="pw">Team password</label>
        <input id="pw" type="password" autoFocus value={password} onChange={(e) => setPassword(e.target.value)}
               autoComplete="current-password" />
        {error && <div className="warn">{error}</div>}
        <div style={{ marginTop: 18 }}>
          <button className="btn" disabled={busy || !password}>{busy ? "Checking…" : "Sign in →"}</button>
        </div>
      </form>
    </main>
  );
}
