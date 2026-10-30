"""snapshot_download that forces IPv4 (WSL on this machine has broken IPv6 routing to huggingface.co).

Usage: ~/vllm-env/bin/python hf_download_ipv4.py <repo_id> [<repo_id> ...]
"""
import socket
import sys

_orig = socket.getaddrinfo


def _ipv4_only(host, *args, **kwargs):
    return [r for r in _orig(host, *args, **kwargs) if r[0] == socket.AF_INET] or _orig(host, *args, **kwargs)


socket.getaddrinfo = _ipv4_only

import os  # noqa: E402

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import snapshot_download  # noqa: E402

for repo in sys.argv[1:]:
    print("downloading", repo, flush=True)
    path = snapshot_download(repo, max_workers=8)
    print("done", repo, "->", path, flush=True)
