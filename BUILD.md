# Windows EXE 构建

## 环境

- Windows 10/11 x64
- Node.js 18+
- （可选，重建引擎用）Python 3.10+ 且已装 `paddleocr`、`pyinstaller`

界面本体（Electron）不依赖 Python；只有「挂机引擎」需要 Python，或用一个打包好的
`douyin_guaji_worker.exe` 代替。

## 构建界面便携版

```powershell
npm install
npm run dist:portable
```

输出：`release/抖音福袋万花筒-2.0.0-portable.exe`，单文件、免安装。

## 构建挂机引擎（可选）

引擎会把 Python + PaddleOCR 一起冻结成单个 exe（体积较大，约 700MB+）：

```powershell
pyinstaller douyin_guaji_worker.spec --noconfirm --distpath dist_build
copy dist_build\douyin_guaji_worker.exe release\
```

把 `douyin_guaji_worker.exe` 放到便携版 exe **同目录**，程序启动时会自动优先使用它；
找不到才回退到本机 Python + `worker.py`。

## 开发调试

```powershell
npm start
```

用户数据、登录 Cookie 和运行日志保存在 Electron 应用数据目录；便携版运行时会保存到
exe 同级的 `data/` 目录，可在软件右上角点「数据目录」打开。

## 调试端口（可选）

设置环境变量 `DYFD_DEBUG_PORT=9335` 后启动，可用 Chrome DevTools 协议接入界面与内置浏览器。
