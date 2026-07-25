"""Run the long Android build and publish status to the temp directory."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def finish_without_windows_symlinks(
    project_root: Path,
    log_file,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Build Android directly when Windows Developer Mode is unavailable."""
    flutter_project = project_root / "build" / "flutter"
    windows_directory = flutter_project / "windows"
    parked_directory = flutter_project / "windows-disabled-for-android-build"
    resolved_build_root = (project_root / "build").resolve()
    resolved_windows = windows_directory.resolve()

    if (
        not windows_directory.is_dir()
        or parked_directory.exists()
        or not resolved_windows.is_relative_to(resolved_build_root)
    ):
        return subprocess.CompletedProcess([], 1)

    log_file.write(
        "\nWindows Developer Mode is unavailable. Temporarily parking the "
        "generated Windows shell; it is not needed for an Android APK.\n"
    )
    log_file.flush()
    windows_directory.rename(parked_directory)
    try:
        return subprocess.run(
            [
                str(Path.home() / "flutter" / "3.44.7" / "bin" / "flutter.bat"),
                "build",
                "apk",
                "--target-platform",
                "android-arm64,android-x64,android-arm",
                "--build-name",
                "0.1.0",
                "--no-version-check",
                "--suppress-analytics",
            ],
            cwd=flutter_project,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            env=environment,
        )
    finally:
        if parked_directory.exists() and not windows_directory.exists():
            parked_directory.rename(windows_directory)


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    temp_dir = Path(tempfile.gettempdir())
    log_path = temp_dir / "resetpath-android-build.log"
    status_path = temp_dir / "resetpath-android-build.status"
    status_path.write_text("RUNNING", encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    with log_path.open("w", encoding="utf-8") as log_file:
        result = subprocess.run(
            [
                sys.executable,
                str(project_root / "tools" / "flet_runner.py"),
                "build",
                "apk",
                "--yes",
                "--no-rich-output",
                "--module-name",
                "app",
                "--exclude",
                ".git",
                ".venv",
                ".flet",
                "build",
                "dist",
                "docs",
                "tests",
                "tools",
                "-v",
            ],
            cwd=project_root,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            env=environment,
        )
        log_file.flush()
        if result.returncode != 0 and "symlink support" in log_path.read_text(
            encoding="utf-8", errors="replace"
        ):
            result = finish_without_windows_symlinks(
                project_root,
                log_file,
                environment,
            )
    status_path.write_text(f"EXIT={result.returncode}", encoding="utf-8")


if __name__ == "__main__":
    main()
