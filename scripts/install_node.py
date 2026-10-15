"""Install a checksum-verified portable Node 24 LTS under ignored var/tools."""

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://nodejs.org/dist/"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "var" / "tools"


def download(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def main():
    releases = json.loads(download(BASE + "index.json"))
    release = next(r for r in releases if r["version"].startswith("v24.") and r["lts"])
    version = release["version"]
    filename = f"node-{version}-win-x64.zip"
    archive = download(BASE + version + "/" + filename)
    checksums = download(BASE + version + "/SHASUMS256.txt").decode()
    expected = next(
        line.split()[0] for line in checksums.splitlines() if line.split()[-1] == filename
    )
    if hashlib.sha256(archive).hexdigest() != expected:
        raise ValueError("Node archive checksum mismatch.")
    TARGET.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        for name in zipped.namelist():
            if not (TARGET / name).resolve().is_relative_to(TARGET.resolve()):
                raise ValueError("Unsafe archive path.")
        zipped.extractall(TARGET)
    print(str(TARGET / filename.removesuffix(".zip")))


if __name__ == "__main__":
    main()
