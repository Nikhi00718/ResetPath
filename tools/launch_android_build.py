"""Launch the Android build without opening a visible console window."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    temp_dir = Path(tempfile.gettempdir())
    status_path = temp_dir / "resetpath-android-build.status"
    log_path = temp_dir / "resetpath-android-build.log"
    status_path.unlink(missing_ok=True)
    log_path.unlink(missing_ok=True)
    creation_flags = (
        subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        if os.name == "nt"
        else 0
    )
    process = subprocess.Popen(
        [
            sys.executable,
            str(project_root / "tools" / "android_build_worker.py"),
        ],
        cwd=project_root,
        creationflags=creation_flags,
    )
    print(process.pid)


if __name__ == "__main__":
    main()
