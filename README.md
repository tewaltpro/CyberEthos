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

## Ideas for further features

- A weekly "digital reflection" summary instead of constant nagging
- A "cooldown" mode: typing a short reason before certain sites unlock, not
  blocking them outright
- Optional local-only journal entry prompt after the panic button fires,
  for the user's own eyes only, never uploaded anywhere

The purpose of the app is simply to be a helping hand to responsibly explore the vast world of the internet to anyone who wants it, as this app is now available entirely for free on the Microsoft Store! In a rapidly changing digital world, it's important to remember that accountability can still exist and that it starts with you doing the right thing from power on until power off. 
