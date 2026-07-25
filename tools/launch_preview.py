"""Launch a hidden Flet web preview for local verification on Windows."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    stdout_path = Path(tempfile.gettempdir()) / "resetpath-flet-out.log"
    stderr_path = Path(tempfile.gettempdir()) / "resetpath-flet-err.log"
    creation_flags = (
        subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        if os.name == "nt"
        else 0
    )
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_file:
        process = subprocess.Popen(
            [
                sys.executable,
                str(project_root / "tools" / "flet_runner.py"),
                "run",
                "--web",
                "--port",
                "8550",
                "app.py",
            ],
            cwd=project_root,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creation_flags,
        )
    print(process.pid)


if __name__ == "__main__":
    main()
