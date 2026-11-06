# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — NumLock Light 1.1.0
import os

here = SPECPATH
SRC = os.path.join(here, '..', 'src', 'numlocklight')

datas = [
    # Bundled Vazirmatn fonts for both Python (Pillow/GDI) and WebUI
    (os.path.join(here, '..', 'assets', 'fonts'), 'assets/fonts'),
    (os.path.join(here, '..', 'assets', 'fonts'), 'numlocklight/webui/fonts'),
    # Icons & sounds
    (os.path.join(here, '..', 'assets', 'icons'), 'assets/icons'),
    (os.path.join(here, '..', 'assets', 'sounds'), 'assets/sounds'),
    # Settings window UI
    (os.path.join(SRC, 'webui', 'index.html'), 'numlocklight/webui'),
    (os.path.join(SRC, 'webui', 'app.css'), 'numlocklight/webui'),
    (os.path.join(SRC, 'webui', 'app.js'), 'numlocklight/webui'),
]

a = Analysis(
    [os.path.join(here, '..', 'run.py')],
    pathex=[os.path.join(here, '..', 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'pystray', 'pystray._win32',
        'six', 'six.moves.queue',
        'arabic_reshaper',
        'bidi', 'bidi.algorithm', 'bidi.bidi',
        'webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium',
        'webview.platforms.mshtml',
        'clr_loader', 'clr_loader.ffi.netfx',
    ],
    # 1.1.0 hotfix (build crash): 'excludes' must NOT contain any of the
    # top-level namespaces that modern setuptools (>= 71) exposes from its
    # vendored directory — distutils, setuptools, jaraco, more_itertools,
    # backports, tomli, wheel, packaging, typing_extensions, zipp, ... —
    # because PyInstaller's pre-safe-import alias hooks die with
    #   ValueError: Target module "..." already imported as ExcludedModule
    # on Python 3.12+ the moment the graph walks setuptools. Only 'pip'
    # (which has no alias hook) is safe to exclude. Reproduced & verified.
    excludes=[
        'pip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NumLockLight',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(here, '..', 'assets', 'icons', 'app.ico'),
    version=os.path.join(here, 'version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='NumLockLight',
)