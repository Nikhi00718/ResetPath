"""Build the ResetPath APK straight from the Android SDK tools.

No Gradle, Flutter, or network access: aapt2 links resources and the web
assets, javac + d8 compile the small native shell, then zipalign and
apksigner produce dist/resetpath.apk.

Usage:
    python tools/build_apk.py [--version-name 1.0.0] [--version-code 3000]

Signing uses the Android debug keystore (~/.android/debug.keystore) unless
RESETPATH_KEYSTORE, RESETPATH_KEY_ALIAS, and RESETPATH_KEYSTORE_PASS are set.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "apk"
DIST = ROOT / "dist"
MIN_SDK = 24
TARGET_SDK = 34


def sdk_root() -> Path:
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(name):
            return Path(os.environ[name])
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk"
    if local.is_dir():
        return local
    return Path.home() / "Android" / "Sdk"


def latest(directory: Path, prefix: str = "") -> Path:
    candidates = sorted(
        (p for p in directory.iterdir() if p.name.startswith(prefix)),
        key=lambda p: [int(part) if part.isdigit() else part for part in p.name.replace("-", ".").split(".")],
    )
    if not candidates:
        sys.exit(f"Nothing matching {prefix!r} in {directory}")
    return candidates[-1]


def tool(build_tools: Path, name: str) -> str:
    for suffix in (".exe", ".bat", ""):
        path = build_tools / f"{name}{suffix}"
        if path.exists():
            return str(path)
    sys.exit(f"Missing build tool {name} in {build_tools}")


def javac() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / ("javac.exe" if os.name == "nt" else "javac")
        if candidate.exists():
            return str(candidate)
    found = shutil.which("javac")
    if not found:
        sys.exit("javac not found. Install a JDK (17 or newer) or set JAVA_HOME.")
    return found


def run(*command: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        print(" ".join(command), file=sys.stderr)
        print(result.stdout, result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-name", default="1.0.0")
    parser.add_argument("--version-code", default="3000")
    args = parser.parse_args()

    sdk = sdk_root()
    build_tools = latest(sdk / "build-tools")
    android_jar = latest(sdk / "platforms", "android-") / "android.jar"
    print(f"SDK {sdk}\nbuild-tools {build_tools.name}, {android_jar.parent.name}")

    shutil.rmtree(BUILD, ignore_errors=True)
    for sub in ("gen", "classes", "dex", "assets"):
        (BUILD / sub).mkdir(parents=True)
    DIST.mkdir(exist_ok=True)

    # Web app goes into assets/web, minus development-only files.
    shutil.copytree(ROOT / "web", BUILD / "assets" / "web", ignore=shutil.ignore_patterns("*.map", ".DS_Store"))

    aapt2 = tool(build_tools, "aapt2")
    run(aapt2, "compile", "--dir", str(ROOT / "android" / "res"), "-o", str(BUILD / "res.zip"))
    unsigned = BUILD / "unsigned.apk"
    run(
        aapt2, "link",
        "-o", str(unsigned),
        "-I", str(android_jar),
        "--manifest", str(ROOT / "android" / "AndroidManifest.xml"),
        "--min-sdk-version", str(MIN_SDK),
        "--target-sdk-version", str(TARGET_SDK),
        "--version-code", args.version_code,
        "--version-name", args.version_name,
        "--java", str(BUILD / "gen"),
        "-A", str(BUILD / "assets"),
        str(BUILD / "res.zip"),
    )

    sources = [str(p) for p in (ROOT / "android" / "src").rglob("*.java")]
    sources += [str(p) for p in (BUILD / "gen").rglob("*.java")]
    run(
        javac(), "-nowarn", "-Xlint:-options",
        "-source", "8", "-target", "8",
        "-bootclasspath", str(android_jar),
        # android.jar has no LambdaMetafactory; d8 desugars lambdas later.
        "-classpath", str(build_tools / "core-lambda-stubs.jar"),
        "-d", str(BUILD / "classes"),
        *sources,
    )

    classes = [str(p) for p in (BUILD / "classes").rglob("*.class")]
    run(
        tool(build_tools, "d8"), "--release",
        "--min-api", str(MIN_SDK),
        "--lib", str(android_jar),
        "--output", str(BUILD / "dex"),
        *classes,
    )
    with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as apk:
        apk.write(BUILD / "dex" / "classes.dex", "classes.dex")

    aligned = BUILD / "aligned.apk"
    run(tool(build_tools, "zipalign"), "-p", "-f", "4", str(unsigned), str(aligned))

    keystore = os.environ.get("RESETPATH_KEYSTORE", str(Path.home() / ".android" / "debug.keystore"))
    alias = os.environ.get("RESETPATH_KEY_ALIAS", "androiddebugkey")
    password = os.environ.get("RESETPATH_KEYSTORE_PASS", "android")
    output = DIST / "resetpath.apk"
    run(
        tool(build_tools, "apksigner"), "sign",
        "--ks", keystore,
        "--ks-key-alias", alias,
        "--ks-pass", f"pass:{password}",
        "--key-pass", f"pass:{password}",
        "--out", str(output),
        str(aligned),
    )
    run(tool(build_tools, "apksigner"), "verify", str(output))
    print(f"Built {output} ({output.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
