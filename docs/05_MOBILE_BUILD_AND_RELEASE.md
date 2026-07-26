# ResetPath Mobile Build and Release

## 1. Current build environment

The first Android build has completed successfully on this Windows workspace.
Flet bootstrapped Flutter 3.44.7, JDK 17, the Android SDK, NDK, CMake, and
Gradle. Those downloads are cached for later builds.

Flet can build Android APK/AAB packages on Windows. iOS packages require macOS.
See the official [Flet platform matrix](https://flet.dev/docs/publish/).

## 2. Android development build

Activate the environment:

```powershell
cd "C:\Users\atnik\Documents\Support app"
.\.venv\Scripts\Activate.ps1
```

Check tooling:

```powershell
flet doctor
```

Build a universal APK:

```powershell
flet build apk --module-name app --yes
```

The universal APK is larger because it includes multiple Android CPU
architectures, but it is easiest for personal installation.

The included background launcher uses the same build and records a log:

```powershell
.\.venv\Scripts\python.exe tools\launch_android_build.py
```

The build worker uses Flet's `--split-per-abi` option. For most physical
Android phones, distribute `resetpath-arm64-v8a.apk`; it is substantially
smaller than a universal APK. Keep the universal build as a compatibility
fallback when one is available.

On Windows, Flutter may ask for Developer Mode because its generated desktop
shell uses plugin symlinks. The included worker has an Android-only fallback
that temporarily parks the generated Windows shell instead of changing the
computer's security settings.

Flet’s [Android packaging guide](https://flet.dev/docs/publish/android/)
documents the build prerequisites and supported architectures.

## 3. Android signing

Android requires signed APKs.

If no upload keystore is supplied, Flet signs the release build with a debug key.
That build is suitable for installing on a personal phone but not for Google
Play.

Important:

- Keep the same debug signing key to update the installed app without
  uninstalling.
- Uninstalling may remove local ResetPath data.
- Do not publish a debug-signed APK to an app store.

For a future Play Store release:

1. create a private upload keystore,
2. keep it outside the repository,
3. keep passwords in environment variables,
4. build an AAB,
5. enable Play App Signing.

Never commit `.jks` files or passwords.

## 4. Save the local APK artifact

After a successful build, locate the APK under:

```text
build/apk/
```

Copy the verified file to:

```text
dist/ResetPath-v0.1.0-android.apk
```

Generate a checksum:

```powershell
Get-FileHash .\dist\ResetPath-v0.1.0-android.apk -Algorithm SHA256
```

Save the output in:

```text
dist/ResetPath-v0.1.0-android.apk.sha256
```

For the verified v0.1.0 build:

```text
SHA-256
0C15A94D75A7A51FF8DCC2576D654156131FCBA15D752FF01EAEAAB400DE021D
```

## 5. Install manually on Android

1. Connect the phone to the computer.
2. Copy `ResetPath-v0.1.0-android.apk` to the phone’s Downloads folder.
3. Open the APK from the phone’s file manager.
4. Android may request permission to install unknown applications.
5. Allow that permission only for the selected file manager.
6. Install ResetPath.
7. Disable the unknown-app permission again.
8. Open the application and complete onboarding.

Only install APKs built from the trusted project source.

## 6. Install with ADB

After Android Platform Tools and USB debugging are available:

```powershell
adb devices
adb install -r .\dist\ResetPath-v0.1.0-android.apk
```

`-r` updates an existing installation while preserving data when the package ID
and signing key remain unchanged.

## 7. Physical-phone verification

Test:

1. onboarding,
2. support-contact configuration,
3. task creation and completion,
4. evidence history,
5. thought-journal response,
6. crisis redirect,
7. charts,
8. export,
9. delete confirmation,
10. dialler links,
11. app restart,
12. phone reboot,
13. offline operation,
14. portrait and landscape layouts.

Do not call the APK verified based only on a desktop or emulator test.

## 8. iPhone build

The same Flet source can target iOS, but `flet build ipa` runs only on macOS.

Requirements:

- Mac,
- Xcode 15 or newer,
- CocoaPods,
- Apple application identifier,
- signing certificate,
- provisioning profile,
- Apple Developer Program access for normal distribution.

On the Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
flet doctor
flet build ipa
```

See the official
[Flet iOS packaging guide](https://flet.dev/docs/publish/ios/).

Before calling iOS complete, verify:

- database persistence,
- file export,
- phone links,
- navigation gestures,
- icon requirements,
- OS backup behaviour,
- signing,
- TestFlight installation.

## 9. Play Store or App Store release

A public release is a separate phase. It requires:

- production signing,
- a privacy policy,
- store screenshots and descriptions,
- data-safety disclosures,
- professional review of safety wording,
- wider device testing,
- a support/contact process,
- release monitoring,
- and a plan for correcting hotline or counsellor information.

The personal version should be completed and tested before beginning public
distribution work.
