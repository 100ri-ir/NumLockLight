# Changelog — NumLock Light

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] — 2026-11-06 — FINAL RELEASE

### Fixed — 1. Every sound was silent (none of the effects ever played)

**Root cause.** The sound engine played volume-scaled buffers through
`winsound.PlaySound(data, SND_MEMORY | SND_ASYNC)`. CPython 3.13+ raises
`RuntimeError: Cannot play asynchronously from memory` for exactly that flag
pair (the async-memory case cannot guarantee buffer lifetime), and the old
engine swallowed the exception with `except Exception: pass` — so every
single effect was silently dropped on Python 3.15.

**Fix (`sound.py` fully rewritten):**
- Talks to `winmm.dll` directly via `ctypes` — `winsound` is no longer
  imported at all (and was removed from the PyInstaller hiddenimports).
- Volume ≥ 99 → original file played `SND_FILENAME|SND_ASYNC|SND_NODEFAULT`.
- Volume < 99 → PCM-scaled WAV image played `SND_MEMORY` **synchronously**
  inside the worker daemon thread, so the buffer is provably alive for the
  whole playback.
- Volume 0 is treated as mute. Playback failures are now logged (first
  few) instead of being silently swallowed.
- The self-check gained a `sound engine (winmm via ctypes)` probe.

### Fixed — 2. Startup took several seconds before the tray appeared

**Root causes.** The startup self-check imported `pywebview` on the critical
path (dragging in bottle/ssl and more), `tkinter` + a full `Tk()` interpreter
were initialized at every launch although the OSD is only needed on the first
key toggle, and a `WM_FONTCHANGE` broadcast could block for up to its full
timeout.

**Fixes (`app.py`, `selfcheck.py`, `assets.py`, `run.py`):**
- Monitor + tray icons now start **first**; the OSD/Tkinter thread starts
  lazily on the first `post()` (first toggle / preview).
- The full self-check runs in a background thread after the app is up;
  pywebview is probed with `importlib.util.find_spec` (no execution) there.
  Only `--check` still performs the real import (`run(full=True)`).
- pywebview is pre-warmed on a worker thread 1.5 s after startup, so the
  first "Settings" click opens quickly without ever blocking startup.
- The `WM_FONTCHANGE` broadcast was removed (`FR_PRIVATE` fonts are
  process-local; other processes never needed the notification).
- `run.py` wraps the app import with a loud, logged crash dialog for
  windowed builds.
- Build diet where it is actually safe: `excludes` reduced to `pip` only —
  the originally planned setuptools/jaraco/tomli/wheel exclusions crash
  the build (see fix 5 below).

### Fixed — 3. The setup installer could not be built ("Inno Setup 6 not found")

**Fix (`build/Build_Installer.bat` rewritten):**
- Searches PATH + all standard Inno Setup 6 locations (including per-user
  installs).
- If missing, installs it automatically via `winget` — and if winget is
  unavailable, downloads and silently installs it from jrsoftware.org.
- If Inno Setup still cannot be installed, falls back to the **IExpress**
  engine that ships with Windows itself: a self-extracting per-user
  installer (no admin rights) with Desktop/Start-Menu shortcuts, an
  Add/Remove-Programs entry and a working uninstaller
  (`build/sfx-template/`).
- `Build_Portable.bat` now kills a running `NumLockLight.exe` before
  cleaning `dist\` — the "Access is denied" build errors were caused by
  the app still running while its own files were being replaced.

### Changed — 4. Correct GitHub links & one-click publishing

- All URLs now point to the real profile/repo:
  `https://github.com/100ri-ir/NumLockLight` (constants.py, webui/app.js,
  Inno Setup script, READMEs).
- New `Publish_To_Github.bat`: one-click publisher — git init/commit, GitHub
  CLI auto-install, browser login, repo creation, push and release upload
  (ZIP + Setup + SHA256SUMS) — with a guided manual fallback.
- New `.gitignore` tuned for this project (source goes to git, binaries go
  to Releases).
- Version resource, installer metadata and all banners updated to 1.1.0.

### Fixed — 5. «Build failed» — PyInstaller crashed during analysis (excludes × setuptools)

**Symptom.** `build\Build_All.bat` died in the PyInstaller step with:
`ValueError: Target module "distutils" already imported as ExcludedModule('distutils',)`

**Root cause.** The initial 1.1.0 `excludes` list contained
`setuptools` / `distutils` / `wheel` / `tomli` / `jaraco` / … Modern
PyInstaller ships pre-safe-import **alias hooks** for every top-level
namespace that setuptools ≥ 71 re-exports from its vendored directory
(`distutils`, `jaraco`, `more_itertools`, `backports`, `tomli`, `wheel`,
`packaging`, `typing_extensions`, …). The moment the dependency graph
walks the setuptools chain, each hook calls `add_alias_module` — and if
that name appears in `excludes`, the analysis dies with the `ValueError`
above. On Python 3.12+ this is unavoidable because `distutils` only
exists through the setuptools shim.

**Fix (`build/NumLockLight.spec`).** The `excludes` list is now `pip`
only (the one name without an alias hook). The exact crash was
reproduced in a clean Python 3.12 + setuptools 84 environment and the
fixed spec was verified to build end-to-end (Analysis → PYZ → EXE →
COLLECT, with all 8 sounds and all 4 Vazirmatn fonts correctly bundled
in `_internal/assets/`).

## [1.0.3] — 2026-11-06

Critical fixes for the "settings window opens but is completely dead / no
tray icon" reports. Found by source-level reproduction against the real
pywebview 6.2.1 + pystray 0.19.5 sources.

### Fixed — 1. Settings window rendered but NOTHING responded

**Root cause.** pywebview injects the JS bridge in two steps: first
`window.pywebview = {api: {}, ...}` (api **empty but truthy**), then — in a
second script — it populates `api` and fires `pywebviewready`. The settings
UI's `waitForBridge()` only checked `window.pywebview && window.pywebview.api`,
which passes during that gap: `BRIDGE.get_manifest()` then threw
*"not a function"*, the `async boot()` promise died, and **no event handler
was ever bound** — a perfectly rendered but 100 % inert settings window
(no section switching, no toggles, no close). Exactly the reported
"تنظیمات باز میشه اونم کاری نمیشه کرد".

**Fix (`webui/app.js` rewritten boot logic):**
- readiness = `pywebviewready` event **or** the api actually containing
  methods (`Object.keys(api).length > 0`), with a 10 s patience window.
- every bridge call resolves **dynamically per call** — real API when
  available, mock data otherwise — so a late-arriving bridge is adopted
  automatically and a missing method can never throw an unhandled
  `TypeError` again.
- `boot()` is fully fault-tolerant: each `await` has its own fallback,
  window chrome (nav/close/minimize/quit) is bound **first**, and if the
  first boot fell back to mock data it re-boots the moment the real bridge
  appears. A visible toast warns when running on sample data.

### Fixed — 2. Bridge handshake was slow and leaked the whole app to JS

**Root cause.** `Bridge` stored the `App` instance as the **public**
attribute `self.app`. pywebview's js_api discovery
(`webview.util.get_functions`) walks every public attribute and *recurses
into non-callable objects*: it enumerated the entire App object graph
(Tray, Monitor, OSD, even the live Tk root — the latter from a non-Tk
thread, raising dozens of swallowed exceptions), leaked internal methods
(`app.quit`, `tray.stop`, …) into `window.pywebview.api`, and made the
injection so slow that the race in fix 1 became near-certain.
Additionally `get_manifest()` shipped ~2.7 MB of base64-embedded fonts
through **two** `evaluate_js` round-trips on every window open.

**Fix (`bridge.py`):** the App reference is now `self._app` (underscore
attributes are skipped by the discovery — the exposed API is exactly the
documented methods), and the redundant `font_css` payload was dropped
(the web UI already loads Vazirmatn through its own CSS `@font-face` with
bundled files + `local()` fallbacks).

### Fixed — 3. Tray could die silently / app uncontrollable

- `Tray.start()` was all-or-nothing: **any** exception while constructing
  ONE of the five pystray icons aborted the whole tray (log-only). Each
  icon is now built and launched independently; a failure disables only
  that icon (`tray.py`).
- `refresh()` re-assigned `icon.icon`/`icon.title` unconditionally, which
  makes pystray destroy + reload the HICON and re-send `NIM_MODIFY` on
  every change — including a redundant pass right after startup that
  raced the setup thread's `NIM_ADD` (briefly destroying the very handle
  the shell was showing). Refresh now applies a per-icon signature cache
  and only touches the icon when its rendered content really changed.
- **Escape hatch (1.0.3):** if NO tray icon could be created at all, the
  settings window opens automatically at startup (with its new **خروج از
  برنامه / Quit** button) — the app can never again end up as an
  invisible, uncontrollable background process.
- New `خروج از برنامه` (Quit application) button in the settings sidebar —
  the settings window is now a complete control surface.

### Fixed — 4. Win32 correctness

- `acquire_single_instance()` read `GetLastError()` through the shared
  `ctypes.windll` loader, whose own bookkeeping can clobber the thread's
  last-error between the `CreateMutexW` call and the read — random
  "already running" false positives (instant exit) or missed second
  instances. All kernel32 calls now use a private
  `WinDLL(use_last_error=True)` with explicit argtypes/restypes and
  `ctypes.get_last_error()`; the activation-event calls got the same
  treatment (`winapi.py`).
- The low-level keyboard hook callback used `c_long` (32-bit) as its
  return type; `LRESULT` is 64-bit on x64 Windows, so
  `CallNextHookEx`'s pass-through value was truncated. Fixed with
  `ctypes.c_ssize_t` and a private `user32` binding with full argtypes
  (`monitor.py`).

### Fixed — 5. Build / project hygiene

- Version resources unified to **1.0.3** (was: 1.0.1 in `__init__.py`,
  1.0.2 in module docstrings, 1.0.1 in the installer/spec/bats).
- CI artifact path fixed: `dist/NumLockLight.exe` never existed (onedir
  produces `dist/NumLockLight/NumLockLight.exe`) — the upload step always
  failed. Now uploads the whole onedir bundle.
- `scripts/verify_fixes.py` updated to the current `icons` API (it still
  called `icons.render` / `icons.render_combined` / `icons._draw_shaped`,
  which were removed in 1.0.2) and extended with a Bridge-surface check.

## [1.0.1] — 2026-11-05

Maintenance release fixing three root-cause defects reported against 1.0.0:
missing tray icon, broken Persian OSD text, and the slow / bloated
installer. No feature removed; no UI redesign; minimal targeted diffs.

### Fixed — 1. System tray did not appear (root cause)

**Root cause.** `tray.py` created five `pystray.Icon`s with
`run_detached()` and then mutated `icon/.title/.visible/.menu` from *two*
extra threads (a 400 ms supervisor thread *and* pystray's own
menu-callback threads), racing the setup thread that performs the initial
`NIM_ADD`. pystray 0.19.5's win32 backend has no locking at all — every
property setter immediately runs `DestroyIcon` / `DestroyMenu` /
`Shell_NotifyIconW` on the calling thread (verified in
`pystray/_win32.py` + `_base.py`). Concurrent writers destroy handles the
tray is still using, and every failure was swallowed by
`except Exception: pass` — leaving no icon and no message anywhere.

**Fix (`src/numlocklight/tray.py`, rewritten lifecycle):**
- A single **tray-writer thread** is now the only thread that touches
  icon properties or `Shell_NotifyIcon`; menu callbacks and the Tk thread
  only `request_refresh()` / enqueue notifications.
- Startup passes explicit `setup=` callbacks that raise per-icon
  *ready events*; the writer waits (bounded) for every icon window before
  the first refresh — the startup race and the brief "combined icon
  flash" are gone.
- Every step logged via the new self-check log; failures are visible
  (see `selfcheck.py` below) instead of `except: pass`.
- Menu *structure* is now assigned only when it actually changes
  (language / enabled keys / tray mode) instead of 2.5× per second.
- **Explorer restart** is handled by pystray itself (`TaskbarCreated` →
  re-`_show()` for visible icons; verified in pystray source). The writer
  keeps `icon.visible` accurate so the re-add works.
- Left-click already activated the *default* menu item (Settings) via
  pystray's `WM_LBUTTONUP` → `Menu.__call__`; unchanged and now covered
  by the checklist.
- Quitting from the tray no longer calls `root.after()` from the pystray
  thread (Tkinter is not thread-safe) — it posts to the Tk thread
  (`app.post`); same fix applied to the webview bridge's `quit_app` and
  `osd_preview`, which ran Tk calls on pywebview worker threads.

### Fixed — 2. Persian OSD text rendered disconnected / reversed

**Root cause.** The OSD pill is drawn by Pillow (`icons.render_osd`).
Pillow **Windows wheels do not ship libraqm**
(python-pillow/Pillow#7126), so `features.check("raqm")` is always
`False` on Windows — and the intended fallback pair
`arabic-reshaper` + `python-bidi` was **commented out of
requirements.txt as "dev-only helpers"**. `_draw_shaped()` therefore fell
through both fallbacks and drew the raw logical string: one isolated
codepoint at a time, left-to-right — exactly the reported symptom.
(The Tk "drag hint" bar in arrange mode has the same Tk-on-Windows
limitation and was never shaped.)

**Fix:**
- `arabic-reshaper>=3.0` + `python-bidi>=0.4.2` are real runtime deps
  (`requirements.txt`) and pinned in the spec's `hiddenimports` (they are
  imported lazily, so static analysis misses them — the exact mechanism
  that let 1.0.0 ship broken).
- New `strings.shape(text)` = `get_display(arabic_reshaper.reshape(text))`
  wraps **every** user-visible Persian string before it reaches Tk or
  raw Pillow (`_draw_shaped` fallback + the arrange-mode hint bar).
  Strings meant for native renderers (Shell tooltips/balloons,
  MessageBoxW) are deliberately *not* shaped — Windows renders them
  correctly itself.
- Verified programmatically (see `scripts/verify_fixes.py`): presentation
  forms present, correct visual order (pure-RTL strings are the exact
  reverse of the shaped logical string; mixed `"NumLock: فعال 123"` keeps
  the Latin prefix and digit order and matches the authoritative
  fribidi/raqm reference layout at ink-IoU 0.97; the two-word template
  test proves RTL word order). The four mandated test strings all pass.
- raqm path kept first when available (Linux/macOS wheels), so nothing
  regresses there.

### Fixed — 3. Installer: thousands of small files, slow install, slow startup

**Root cause.** The 1.0.0 release artifacts were built through the
*bundled-runtime* path (`build/embedded/`: native launcher + full
conda-style embedded Python 3.12 tree with `include/`, tests, `Library/`)
— installed via NSIS: thousands of small files, slow installs. The
Inno/PyInstaller path that also existed built a **onefile** EXE, which
extracts itself to `%TEMP%` on every launch (slow cold start, stale
folders after crashes).

**Fix (`build/NumLockLight.spec`, `build/NumLockLight.iss`, build bats):**
- Standard flow is now **PyInstaller onedir + Inno Setup** — fast start
  (no %TEMP% extraction), nothing left behind, and Inno compresses the
  tree with `lzma2/ultra64` + `SolidCompression=yes`.
- Asset diet: fonts ship **once** (`assets/fonts`; the settings web UI now
  points at them through a CSS fallback URL instead of carrying its own
  identical copies); `assets/icons` trimmed to the two files the code
  reads; the 8 CC0 WAVs (~230 KB total) stay as-is (winsound cannot play
  OGG/MP3, so transcoding would trade a feature for ~150 KB).
- `hiddenimports` finalized (pystray._win32 + six.moves.queue +
  arabic_reshaper + bidi + winsound + pywebview platforms;
  WebView2/pythonnet runtime DLLs come from the hooks those packages ship
  with their wheels). `excludes`: tkinter.test / test / unittest / pydoc /
  pydoc_data / lib2to3 / distutils — **tkinter itself stays** (it is the
  OSD host). UPX disabled (AV false positives, no benefit inside lzma2).
- `build/embedded/` kept for history but marked deprecated and no longer
  called by any build script.
- Uninstall removes the app dir; `%APPDATA%\NumLockLight` user data is
  kept **unless the user opts in** (confirmation box at uninstall).
- `Fetch_Assets.py` remains **build-time only**; the installer ships
  pre-fetched, pre-built assets — no network, no pip, no git at install
  time (verified: nothing in the `.iss` touches the network).

### Added

- `src/numlocklight/selfcheck.py`: startup self-check + log file
  (`NumLockLight.log` next to `settings.json`). Verifies pystray + its
  win32 backend, Pillow (+raqm status), arabic-reshaper/python-bidi,
  pywebview, WebView2 runtime, fonts/icons/sounds. Fatal problems (app
  uncontrollable) show a native message box instead of starting a zombie
  process; `NumLockLight.exe --check` runs the self-check on demand.
  All tray/OSD code paths now log instead of `except: pass`.
- Single-instance **activation**: a second launch now wakes the first
  instance (opens/focuses the settings window) through a named
  auto-reset kernel event, instead of only showing "already running".
  The mutex moved `Global\` → `Local\` (per-user — a second Windows
  user on fast-user-switching can now run their own instance).
- `spike/`: Step-0 PySide6 spike + measurements that justify staying on
  the current stack (see `spike/SPIKE-RESULT.md` — NO-GO for migration:
  both bugs were code-level, and Qt costs ~83 MB of wheels for no new
  capability).
- `scripts/verify_fixes.py`: automated verification suite (33 checks,
  runs headless; see BUILD-REPORT.md for results).

### Manual test checklist (PACKAGED exe — Win10 & Win11)

Run on **both** Windows 10 (1903+) and Windows 11 after
`Build_All.bat`. Time each step where noted. Report deviations with the
`NumLockLight.log` excerpt.

| # | Test | Expected | Win10 | Win11 |
|---|------|----------|-------|-------|
| 1 | Cold start (after reboot, SSD): launch exe, stopwatch until tray icon visible | icon ≤ 2 s; log line "first refresh applied … ms" | ☐ | ☐ |
| 2 | Warm start: launch again | icon ≤ 1 s | ☐ | ☐ |
| 3 | Right-click tray icon | Menu: toggle Num/Caps(+ScrLk/Ins if enabled), Settings, Preview notification, Indicator enabled, Start with Windows, About, Exit — all entries respond | ☐ | ☐ |
| 4 | Left-click / double-click tray icon | Settings window opens / focuses | ☐ | ☐ |
| 5 | Close the settings window | Hides to tray; process still running; icon still there | ☐ | ☐ |
| 6 | Toggle NumLock on the physical keyboard | OSD shows shaped, correctly-ordered Persian; sound plays if enabled; tray icon color flips | ☐ | ☐ |
| 7 | OSD test strings (set language=fa, press NumLock several times; compare with Settings→OSD preview) | "قفل اعداد روشن"-style text: letters JOINED, reads right-to-left; digits/English inside Persian keep logical order | ☐ | ☐ |
| 8 | OSD drag-to-place (Settings → "جابه‌جایی با کشیدن") | Hint bar itself renders shaped Persian; drag works; position persists after restart | ☐ | ☐ |
| 9 | Launch a second copy (exe again / shortcut) | No second tray icon; settings window of first instance opens/focuses; second process exits silently | ☐ | ☐ |
| 10 | Explorer restart: `taskkill /f /im explorer.exe & start explorer` | Tray icon reappears automatically within ~2 s | ☐ | ☐ |
| 11 | Tray style/size/mode changes in Settings | Tray icon updates within ≤ 0.4 s, no ghost icons, no crash | ☐ | ☐ |
| 12 | Settings persistence: change language/colors, restart app | Changes persist (portable: `NumLockLight_Data` next to exe; installed: `%APPDATA%\NumLockLight`) | ☐ | ☐ |
| 13 | Install from `NumLockLight-Setup-1.0.1.exe` (SSD) | Completes < 30 s; note the reported time + installed size | ☐ | ☐ |
| 14 | Uninstall | App dir gone; no leftover files except `%APPDATA%\NumLockLight` **unless** user chose to delete it in the final dialog | ☐ | ☐ |
| 15 | `NumLockLight.exe --check` | Self-check prints OK (or precise missing-dep list) + log path | ☐ | ☐ |
| 16 | No-network install: firewall on, install again | Installer completes; no network prompts (assets are pre-baked) | ☐ | ☐ |

### Known limitations (unchanged / accepted)

- Menu *structure* updates (language change, enabling a key) still assign
  `icon.menu` cross-thread — required by pystray's API; now happens only
  on change instead of 2.5×/s. If the tray menu is open at that exact
  moment it can close once.
- Without libraqm (all Windows Pillow wheels) the fallback shaping has
  no harfbuzz kerning/ligatures; text is correct, marginally less pretty
  than a raqm build.
- `Global\` → `Local\` mutex: instances are now per-user; two different
  Windows users can run the app simultaneously (intended).

## [1.0.0] — 2026-11-05

The "final" release — complete UI rebuild on a web engine, per user feedback.

### Changed (breaking redesign)
- **Settings window rebuilt as a web UI** (pywebview + WebView2): pixel-perfect
  RTL/LTR mirroring via CSS logical properties, modern glassy design, custom
  frameless title bar. The old Tkinter settings window (`settings_window.py`,
  `ui_kit.py`) is gone.
- **Base layout is language-agnostic**: English first, Persian as a full
  translation — switching language only swaps strings and direction, nothing
  breaks (`language: fa|en` setting, default `fa`).
- **Universal state colors**: every key now follows green = ON / red = OFF
  (v2 per-key hues are migrated automatically to the new scheme).
- **Tray icon default style is "Letter badge"** so each icon shows its key's
  letter; the combined single icon now shows four letter tiles instead of
  ambiguous dots.
- Sound volume is applied by scaling PCM samples in memory — the **system
  wave volume is never touched anymore**.

### Added
- **Low-level keyboard hook (WH_KEYBOARD_LL)** in `monitor.py`: instant,
  100% accurate toggle detection from any source (physical/virtual keyboard,
  RDP, scripts), with double-read confirmation after each event and a slow
  safety poll as fallback; the hook thread pumps messages so `GetKeyState`
  toggle bits are authoritative.
- **Key status tiles** at the top of the settings window: big clickable
  keycaps, green glow when ON / red when OFF, live-updating with a flash
  animation — clicking a tile toggles that key.
- **OSD drag-to-place**: "جابه‌جایی با کشیدن ماوس" enters arrange mode —
  drag the pill anywhere, release/double-click/Enter to save, Esc to cancel.
  Position is stored as a fraction of the monitor work area.
- **Precise OSD placement** on the monitor under the cursor (taskbar
  excluded, multi-monitor safe, DPI aware) — no more wrong corners.
- **Live taskbar preview** in Appearance plus real rendered previews of all
  six icon styles.
- WebView2 runtime detection with a friendly download prompt (Windows 10/11
  ship it preinstalled).
- Settings schema v3 with automatic migration from v2.

### Fixed
- Persian text shaping in the OSD (raqm-backed rendering with reshaper
  fallback) and correct text direction in every widget. *(Superseded by the
  1.0.1 root-cause fix: the fallback pair was not actually installable.)*
- Sliders now always track the mouse exactly (native HTML range inputs) —
  the reversed-drag bug of the old custom widgets is gone.
- Insert-key toggle uses `SendInput` with the extended-key flag.
- `python __main__.py` direct execution works (no relative-import crash).

## [0.x history] — 2026-11-04/05

### [2.0.1]
- Fixed `ImportError` when running `__main__.py` directly; run-at-startup
  prefers the bundled launcher EXE.

### [2.0.0]
- Multi-key monitoring (Caps/Scroll/Insert), 6 icon styles, animated OSD,
  sound feedback, themes, tray toggles, balloon tips, single-instance,
  HiDPI, portable mode, v1 settings migration, NSIS installer, CI.

### [1.x] — 2025
- Initial release: Num Lock tray indicator with on/off colors,
  run-at-startup, Persian settings dialog.

[sadri1993 — 100ri.ir](https://100ri.ir)
