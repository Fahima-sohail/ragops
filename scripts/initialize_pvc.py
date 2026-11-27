"""Initialize an empty Kubernetes persistence volume from the image fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path


def copy_if_empty(source: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    preserved = 0
    for child in source.iterdir():
        target = destination / child.name
        if target.exists():
            preserved += 1
            continue
        if child.is_dir():
            shutil.copytree(child, target)
        elif child.is_file():
            shutil.copy2(child, target)
        copied += 1
    print(f"initialized {destination}; copied {copied} missing entries, preserved {preserved}")
    return copied


def main() -> int:
    root = Path("/app")
    persistent = Path("/app/persist")
    for name in ("batch_a", "batch_b"):
        copy_if_empty(root / "data" / name, persistent / name)
    for name in ("quarantine", "archive", "traces", "results"):
        (persistent / name).mkdir(parents=True, exist_ok=True)
    # Keep the measured gate fixtures available to Jobs on a clean claim.
    results = persistent / "results"
    for filename in ("C2_baseline.json", "C2_candidate_pass.json", "C2_candidate_fail.json"):
        source = root / "eval" / "results" / filename
        target = results / filename
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)
            print(f"seeded gate fixture {target.name}")
    measured_baseline = results / "C2_baseline.json"
    stable_baseline = results / "baseline.json"
    if measured_baseline.is_file() and not stable_baseline.exists():
        shutil.copy2(measured_baseline, stable_baseline)
        print("seeded baseline.json from the measured TOP_K=3 baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
