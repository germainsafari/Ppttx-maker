"""Convert files to LF line endings (and UTF-8): python tools/lf.py file1 file2 ..."""
import sys

for p in sys.argv[1:]:
    with open(p, "rb") as f:
        data = f.read()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(data) > 1 and data[1] == 0):
        data = data.decode("utf-16").encode("utf-8")
    with open(p, "wb") as f:
        f.write(data.replace(b"\r\n", b"\n"))
    print("lf:", p)
