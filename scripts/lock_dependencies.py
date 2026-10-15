"""Capture a tested dependency closure, including optional evaluation extras."""

import argparse
import platform
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def requirements_from(path, seen=None):
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return
    seen.add(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-c "):
            continue
        if line.startswith("-r "):
            yield from requirements_from(path.parent / line[3:].strip(), seen)
        else:
            yield Requirement(line)


def capture(requirements, get_distribution=distribution):
    pending, platform_lines = [], []
    for req in requirements:
        if req.marker and not req.marker.evaluate():
            platform_lines.append(str(req))
        else:
            pending.append(req)
    pinned, visited = {}, set()
    while pending:
        req = pending.pop()
        name = canonicalize_name(req.name)
        key = (name, frozenset(req.extras))
        if key in visited:
            continue
        visited.add(key)
        try:
            installed = get_distribution(name)
        except PackageNotFoundError:
            raise RuntimeError(f"Required installed package missing: {name}") from None
        if req.specifier and installed.version not in req.specifier:
            raise RuntimeError(f"Installed {name} version does not satisfy {req}.")
        pinned[name] = installed.version
        for dependency in installed.requires or []:
            child = Requirement(dependency)
            if not child.marker or any(
                child.marker.evaluate({"extra": extra}) for extra in ("", *req.extras)
            ):
                pending.append(child)
    return pinned, platform_lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", default="requirements.txt")
    parser.add_argument("--output", default="requirements.lock")
    args = parser.parse_args()
    pinned, platform_lines = capture(requirements_from(ROOT / args.requirements))
    text = f"# Tested {platform.system()}/Python {platform.python_version()} dependency closure; Linux-specific dependencies are resolved on Linux.\n"
    text += "\n".join(f"{name}=={version}" for name, version in sorted(pinned.items()))
    text += "\n" + "\n".join(platform_lines) + "\n"
    (ROOT / args.output).write_text(text, encoding="utf-8")
    print(f"Captured {len(pinned)} installed package versions in {args.output}.")


if __name__ == "__main__":
    main()
