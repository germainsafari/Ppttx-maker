"""End-to-end test of the HTTP API, exactly as the web app uses it.

    python tests/e2e_api.py [--url http://localhost:8090] [--key KEY | --secret SECRET] [-f file ...]
"""
import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import httpx


def mint(secret: str, ttl: int = 600) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "e2e", "exp": int(time.time()) + ttl}).encode()).rstrip(b"=")
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), payload, hashlib.sha256).digest()).rstrip(b"=")
    return f"{payload.decode()}.{sig.decode()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8090")
    ap.add_argument("--key")
    ap.add_argument("--secret")
    ap.add_argument("-f", "--file", action="append", default=[])
    ap.add_argument("-p", "--prompt", default="Summarise this survey for the management team: key results, "
                                              "strengths, pain points and recommended actions.")
    ap.add_argument("-n", "--slides", type=int, default=8)
    ap.add_argument("-o", "--out", default="tests/out/e2e")
    a = ap.parse_args()

    headers = {"X-API-Key": a.key} if a.key else {"Authorization": f"Bearer {mint(a.secret)}"} if a.secret else {}
    c = httpx.Client(base_url=a.url, headers=headers, timeout=120)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print("health:", c.get("/api/health").json())
    if a.key or a.secret:
        r = httpx.post(f"{a.url}/api/jobs", data={"prompt": "x"}, timeout=30)
        print("unauthenticated request ->", r.status_code)
        assert r.status_code == 401, "engine accepted a request without credentials"

    files = [("files", (Path(f).name, Path(f).read_bytes())) for f in a.file]
    t0 = time.time()
    r = c.post("/api/jobs", data={"prompt": a.prompt, "slide_count": str(a.slides), "language": "auto"}, files=files)
    r.raise_for_status()
    job_id = r.json()["id"]
    print("job:", job_id)

    last = ""
    while True:
        job = c.get(f"/api/jobs/{job_id}").json()
        if job["message"] != last:
            print(f"  {time.time() - t0:5.1f}s {job['progress']:.0%} {job['message']}")
            last = job["message"]
        if job["status"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert job["status"] == "done", job["message"]
    print("timings:", job["timings"], "| previews:", job["previews"], "| warnings:", job["warnings"])

    deck = c.get(f"/api/jobs/{job_id}/deck.pptx")
    deck.raise_for_status()
    (out / "deck.pptx").write_bytes(deck.content)
    print("downloaded deck.pptx:", len(deck.content) // 1024, "KB,", deck.headers.get("content-disposition"))
    for i in range(1, job["previews"] + 1):
        (out / f"{i:02d}.png").write_bytes(c.get(f"/api/jobs/{job_id}/previews/{i}.png").content)

    spec = c.get(f"/api/jobs/{job_id}/spec").json()
    target = next(i for i, s in enumerate(spec["slides"], 1) if s["type"] not in ("cover", "agenda", "section",
                                                                                 "closing"))
    t1 = time.time()
    r = c.post(f"/api/jobs/{job_id}/revise", json={"slide": target, "instruction": "Make it shorter and punchier."})
    r.raise_for_status()
    print(f"revised slide {target} in {time.time() - t1:.1f}s:", json.dumps(r.json()["slide"], ensure_ascii=False)[:300])
    (out / f"{target:02d}_revised.png").write_bytes(c.get(f"/api/jobs/{job_id}/previews/{target}.png").content)
    print(f"OK in {time.time() - t0:.1f}s -> {out}")


if __name__ == "__main__":
    sys.exit(main())
