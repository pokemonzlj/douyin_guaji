# 抖音福袋万花筒

Windows 桌面版抖音福袋挂机工具。界面用 Electron，真正的抢福袋引擎走 **ADB + 手机端抖音 App + PaddleOCR**。

## 为什么不用网页版

抖音网页版已经下线福袋功能：调用 `/webcast/lottery/melon/lottery_info/` 会返回

```json
{"prompts":"系统升级中，暂不支持"}
```

也就是网页端再怎么写签名、怎么调接口都拿不到福袋。福袋只存在于**手机端抖音 App**，所以本工具的抓取引擎必须跑在手机/模拟器上。

## 两种运行模式

界面里有两块功能：

1. **挂机引擎（真机）** —— 主功能。通过 ADB 操作手机端抖音，OCR 识别屏幕上的福袋并自动参与。
2. **网页扫描（实验）** —— 内置浏览器会话，只用于查看直播间和登录，抓不到福袋（原因见上）。

## 使用（真机引擎）

1. 准备一台手机或安卓模拟器，安装最新版**手机端抖音 App**，并登录账号。
2. 打开手机的「开发者选项 → USB 调试」，用数据线连到本电脑。
3. 命令行执行 `adb devices`，能看到设备序列号才算连上（模拟器一般已自动连上）。
4. 打开本工具，在「挂机引擎（真机）」里点「刷新设备」，选择你的设备，点「启动挂机」。
5. **启动前请先在手机上把抖音打开**，停在任意直播间（或关注页的直播列表）——引擎靠识别屏幕上的福袋图标工作，不会自己去启动 App。
6. 引擎首次启动会加载 OCR 模型（约 10 秒），之后自动识别福袋并参与，运行日志实时显示进度。

> 注意：引擎沿用原作者的夜间休眠设计——**凌晨 1 点到 7 点之间不会抢福袋**，会自动关闭抖音等待。白天运行即可。

## 引擎来源（自动查找顺序）

程序按以下顺序寻找引擎，找到哪个用哪个：

1. 程序同目录下的 `douyin_guaji_worker.exe`（打包好的独立引擎，放到 exe 旁即可，无需 Python）
2. 程序自带资源里的引擎源码 `resources/assets/engine/worker.py` + 本机 Python
3. 开发目录里的 `worker.py` + 本机 Python

也就是说：**只要本机装了 Python 且带 `paddleocr`，直接双击 exe 就能用**；若目标机器没有 Python，
把 `douyin_guaji_worker.exe` 放到 exe 同目录即可。

## 构建

```powershell
npm install
npm run dist:portable
```

便携版输出到 `release/抖音福袋万花筒-2.0.0-portable.exe`，无需安装。

若要让程序在**没装 Python 的电脑**上也能用，需要把冻结好的引擎放到 exe 同目录：

```powershell
pyinstaller douyin_guaji_worker.spec --noconfirm
copy dist\douyin_guaji_worker.exe release\douyin_guaji_worker.exe
```

开发运行：

```powershell
npm start
```

用户数据、登录 Cookie 和运行日志保存在数据目录（便携版是 exe 同级的 `data/`），可在软件右上角点「数据目录」打开。

## 实现说明

- 挂机动作完全在手机端抖音 App 里完成（点击、滑动、OCR），不伪造或绕过抖音验证码与风控。
- 需要关注 / 评论 / 钻石的福袋按 `config.json` 里的开关处理。
- 分辨率自动适配：引擎启动时读取设备 `wm size`，按比例换算所有点击坐标。
