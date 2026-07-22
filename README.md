# CyberEthos

A small toolkit encouraging thoughtful, responsible internet use.

- `desktop_app/` — Python/PySide6 tray app: boot-time responsibility quote,
  a global panic hotkey (default `Ctrl+Alt+P`) that closes browsers and shows
  a calming affirmation overlay, with an opt-in network-cutoff toggle.
- `browser_extension/` — Chrome/Edge extension (Manifest V3) that pauses file
  uploads and downloads with a brief reflection prompt before letting them
  through.

## Why two separate pieces?

A single app cannot reliably intercept "any upload to any service" at the
operating system level without deep, driver-level hooks — the kind of
behavior antivirus software and Windows SmartScreen are specifically built to
flag as spyware/keylogger-like. The browser extension covers uploads and
downloads for the overwhelming majority of real-world cases (email, cloud
storage, social media, chat apps in-browser) safely and transparently.

## Running the desktop app locally

```
cd desktop_app
pip install -r requirements.txt
python main.py
```

Run as Administrator on Windows if you want the global hotkey and the
optional network-cutoff feature to work reliably — regular user accounts
can't always register system-wide hotkeys or toggle network adapters.

## Loading the browser extension locally (for testing today)

1. Go to `edge://extensions` or `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `browser_extension` folder

This works immediately, no store review needed — good enough to actually use
today while the store submission is in progress.

## Publishing to GitHub (doable today)

This repo includes a GitHub Actions workflow (`.github/workflows/build-release.yml`)
that does the building for you — no local Windows machine or PyInstaller setup
needed on your end.

```
git init
git add .
git commit -m "Initial CyberEthos release"
git branch -M main
git remote add origin https://github.com/<your-username>/CyberEthos.git
git push -u origin main

git tag v1.0.0
git push origin v1.0.0
```

Pushing the tag triggers the workflow. It will:
1. Spin up a real `windows-latest` runner
2. Install your `requirements.txt` and PyInstaller
3. Build `CyberEthos.exe` (bundling `icon.ico`, `quotes.json`, `affirmations.json`)
4. Zip up the browser extension folder
5. Create a GitHub Release on that tag with both files attached

Watch progress under the repo's "Actions" tab. It typically finishes in a
few minutes. If you push more commits and want a new release, just push a
new tag (`v1.0.1`, etc.) — old tags won't retrigger it.

You can also trigger a build without a release by using "Run workflow" on
the Actions tab (useful for testing before you're ready to tag a release).


## Publishing to the Microsoft Store (submit today, live in a few days)

1. Registration is now free for individual developers, but requires
   ID + selfie verification through Partner Center — do this step first
   since verification isn't instant.
2. Package the PyInstaller `.exe` into an MSIX package (MSIX Packaging Tool,
   free from Microsoft, or `msix` via `pip`).
3. Submit through Partner Center. First-time app certification typically
   takes 1-3 business days. It will not be live today, but the submission
   itself can go in today.
4. Heads up: PyInstaller executables are unsigned by default and can trigger
   SmartScreen warnings on first run. Code-signing (even a free/self-signed
   cert for testing, or eventually a proper cert) reduces this friction.

## Publishing the extension (Chrome Web Store / Edge Add-ons)

Both have their own review queues (typically hours to a few days), separate
from the Microsoft Store submission for the desktop app.

## Ideas for further features

- A weekly "digital reflection" summary instead of constant nagging
- A "cooldown" mode: typing a short reason before certain sites unlock, not
  blocking them outright
- Optional local-only journal entry prompt after the panic button fires,
  for the user's own eyes only, never uploaded anywhere
