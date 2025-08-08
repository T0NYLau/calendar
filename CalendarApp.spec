# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\自建资料\\test\\calendar\\calendar_app.py'],
    pathex=[],
    binaries=[],
    datas=[('lunar.js', '.'), ('calendar_data.db', '.'), ('calendar_app_update.py', '.'), ('download_lunar.py', '.'), ('lunar_js_integration.py', '.')],
    hiddenimports=['PIL', 'PIL.Image', 'PIL.ImageDraw', 'pystray', 'requests', 'lunar_python', 'lunar_js_integration'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    name='CalendarApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
