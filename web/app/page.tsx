"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Job = {
  id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  warnings: string[];
  timings: Record<string, number>;
  previews: number;
  model?: string;
  revision?: number;
};

type Conn = { engineUrl: string; token: string };

const ACCEPT = ".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.webp";

export default function Home() {
  const [conn, setConn] = useState<Conn | null>(null);
  const [health, setHealth] = useState<{ ok: boolean; llm?: { model: string; max_model_len: number } } | null>(null);
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [slides, setSlides] = useState(10);
  const [language, setLanguage] = useState("auto");
  const [over, setOver] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [instruction, setInstruction] = useState("");
  const [revising, setRevising] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/api/token")
      .then((r) => r.json())
      .then((c: Conn) => {
        setConn(c);
        return fetch(`${c.engineUrl}/api/health`).then((r) => r.json());
      })
      .then(setHealth)
      .catch(() => setHealth({ ok: false }));
  }, []);

  const authHeaders = useCallback(
    (): Record<string, string> => (conn?.token ? { Authorization: `Bearer ${conn.token}` } : {}),
    [conn]
  );
  const q = conn?.token ? `?token=${encodeURIComponent(conn.token)}` : "";

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "error" || !conn) return;
    const t = setInterval(async () => {
      const r = await fetch(`${conn.engineUrl}/api/jobs/${job.id}`, { headers: authHeaders() });
      if (r.ok) setJob(await r.json());
    }, 1500);
    return () => clearInterval(t);
  }, [job, conn, authHeaders]);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    setFiles((f) => [...f, ...Array.from(list)].slice(0, 10));
  };

  const submit = async () => {
    if (!conn) return;
    setError("");
    setSelected(null);
    const fd = new FormData();
    fd.append("prompt", prompt);
    fd.append("slide_count", String(slides));
    fd.append("language", language);
    files.forEach((f) => fd.append("files", f));
    const r = await fetch(`${conn.engineUrl}/api/jobs`, { method: "POST", body: fd, headers: authHeaders() });
    if (!r.ok) {
      setError(`Engine error ${r.status}: ${await r.text()}`);
      return;
    }
    const { id } = await r.json();
    setJob({ id, status: "queued", progress: 0, message: "Queued", warnings: [], timings: {}, previews: 0 });
  };

  const revise = async () => {
    if (!conn || !job || selected === null || !instruction.trim()) return;
    setRevising(true);
    const r = await fetch(`${conn.engineUrl}/api/jobs/${job.id}/revise`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ slide: selected, instruction }),
    });
    setRevising(false);
    if (!r.ok) {
      setError(`Revision failed: ${await r.text()}`);
      return;
    }
    setInstruction("");
    const j = await fetch(`${conn.engineUrl}/api/jobs/${job.id}`, { headers: authHeaders() });
    setJob(await j.json());
  };

  const busy = job && (job.status === "queued" || job.status === "running");
  const bust = job?.revision ? `&v=${job.revision}` : "";

  return (
    <main className="wrap">
      <div className="eyebrow">Admind deck builder</div>
      <h1>
        From brief to branded deck<span style={{ color: "var(--coral)" }}>_</span>
      </h1>
      <p className="lead">
        Upload your material, describe the presentation, get an editable PowerPoint in Admind style. Everything runs
        on our own GPU — no data leaves Admind.
      </p>
      <p className="muted">
        <span className="status-dot" style={{ background: health?.ok ? "var(--teal-text)" : "var(--coral)" }} />
        {health === null
          ? "Connecting to engine…"
          : health.ok
            ? `Engine online · ${health.llm?.model} · ${Math.round((health.llm?.max_model_len || 0) / 1024)}k context`
            : "Engine offline — check the GPU server and the tunnel"}
      </p>

      <div className="grid">
        <div className="card">
          <label htmlFor="prompt">What should the presentation do?</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. A 10-slide deck for the Board summarising the Q3 brand tracking results: key numbers, what changed vs. Q2, and three recommended actions."
          />
          <div className="row">
            <div>
              <label htmlFor="slides">Slides</label>
              <input id="slides" type="number" min={4} max={25} value={slides} onChange={(e) => setSlides(+e.target.value)} />
            </div>
            <div>
              <label htmlFor="lang">Language</label>
              <select id="lang" value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="auto">Same as prompt</option>
                <option value="English">English</option>
                <option value="Polish">Polish</option>
                <option value="German">German</option>
                <option value="French">French</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: 22 }}>
            <button className="btn" disabled={!prompt.trim() || !!busy || !conn} onClick={submit}>
              {busy ? "Generating…" : "Generate presentation →"}
            </button>
          </div>
          {error && <div className="warn">{error}</div>}
        </div>

        <div className="card">
          <label>Source material</label>
          <div
            className={`drop ${over ? "over" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setOver(true);
            }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setOver(false);
              addFiles(e.dataTransfer.files);
            }}
          >
            Drop files or click to browse
            <div className="muted" style={{ marginTop: 6 }}>PDF, Word, PowerPoint, Excel/CSV, text, images</div>
            <input ref={inputRef} type="file" multiple accept={ACCEPT} hidden onChange={(e) => addFiles(e.target.files)} />
          </div>
          <ul className="files">
            {files.map((f, i) => (
              <li key={i}>
                <span>{f.name} <span className="muted">({Math.round(f.size / 1024)} KB)</span></span>
                <button onClick={() => setFiles(files.filter((_, k) => k !== i))}>remove</button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {job && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="eyebrow">{job.status === "done" ? "Ready" : job.status === "error" ? "Failed" : "Working"}</div>
          {job.status !== "done" && (
            <>
              <div className="bar"><div style={{ width: `${Math.round(job.progress * 100)}%` }} /></div>
              <div className="muted">{job.message}</div>
            </>
          )}
          {job.status === "done" && conn && (
            <>
              <div className="row" style={{ alignItems: "center" }}>
                <a className="btn alt" href={`${conn.engineUrl}/api/jobs/${job.id}/deck.pptx${q}`}>Download .pptx</a>
                <span className="muted">
                  Generated in {job.timings.total}s by {job.model} on the Admind GPU
                </span>
              </div>
              {job.warnings.map((w, i) => (
                <div className="warn" key={i}>Check: {w}</div>
              ))}
              {job.previews > 0 && (
                <>
                  <div className="slides">
                    {Array.from({ length: job.previews }, (_, i) => i + 1).map((n) => (
                      <div key={n} className={`slide ${selected === n ? "sel" : ""}`} onClick={() => setSelected(n)}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={`${conn.engineUrl}/api/jobs/${job.id}/previews/${n}.png${q}${bust}`} alt={`Slide ${n}`} />
                        <span>{n}</span>
                      </div>
                    ))}
                  </div>
                  <div className="row" style={{ alignItems: "end" }}>
                    <div style={{ flex: 3 }}>
                      <label>{selected ? `Revise slide ${selected}` : "Click a slide to revise it"}</label>
                      <textarea
                        style={{ minHeight: 60 }}
                        value={instruction}
                        disabled={!selected}
                        onChange={(e) => setInstruction(e.target.value)}
                        placeholder="e.g. Make it shorter and focus on the eNPS change"
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <button className="btn" disabled={!selected || revising || !instruction.trim()} onClick={revise}>
                        {revising ? "Revising…" : "Apply"}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </>
          )}
          {job.status === "error" && <div className="warn">{job.message}</div>}
        </div>
      )}

      <div className="steps">
        <div><b>01</b>Your files are parsed on our server; images and scans are read by the vision model.</div>
        <div><b>02</b>A local Qwen model plans the storyline and writes each slide as structured data.</div>
        <div><b>03</b>Code renders native, editable charts, diagrams and animations in the Admind template.</div>
      </div>
    </main>
  );
}
