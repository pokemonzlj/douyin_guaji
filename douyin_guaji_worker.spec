# -*- mode: python ; coding: utf-8 -*-
"""冻结 ADB 挂机引擎。

要点：PaddleOCR 3.x 依赖 paddlex，其流水线配置是包内的 YAML 文件，
必须用 collect_data_files 打进去，否则运行时报
"The pipeline (OCR) does not exist!"。
"""
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

datas = []
binaries = []
hiddenimports = []

# paddlex 用 importlib.metadata.version(dep) 判断额外依赖是否可用，缺 .dist-info 会把
# 已装好的依赖全判为缺失，从而抛 DependencyError（OCR requires additional dependencies）。
# 因此把所有已安装分发的元数据一并打入。
import importlib.metadata as _md

_dist_names = set()
try:
    for _d in _md.distributions():
        _n = _d.metadata.get("Name")
        if _n:
            _dist_names.add(_n)
except Exception as _exc:  # pragma: no cover
    print("list distributions failed: %r" % (_exc,))

_meta_ok = 0
for _n in sorted(_dist_names):
    try:
        datas += copy_metadata(_n)
        _meta_ok += 1
    except Exception:  # pragma: no cover
        pass
print("copied metadata for %d distributions" % _meta_ok)

# paddlex / paddleocr 的配置 YAML、资源文件
for _pkg in ("paddlex", "paddleocr"):
    try:
        datas += collect_data_files(_pkg)
        hiddenimports += collect_submodules(_pkg)
    except Exception as _exc:  # pragma: no cover
        print("collect %s failed: %r" % (_pkg, _exc))

# paddle 的原生动态库
try:
    binaries += collect_dynamic_libs("paddle")
    hiddenimports += collect_submodules("paddle")
except Exception as _exc:  # pragma: no cover
    print("collect paddle failed: %r" % (_exc,))

# 其它常被漏掉的依赖
hiddenimports += [
    "pyclipper",
    "shapely",
    "skimage",
    "scipy",
    "scipy.special",
    "scipy._lib.messagestream",
    "cv2",
    "PIL",
    "lxml.etree",
    "websocket",
    "requests",
    "tqdm",
]

a = Analysis(
    ['worker.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide6', 'PyQt6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='douyin_guaji_worker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
