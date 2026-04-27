"""
maa_controller.py
=================
基于 MaaFramework 的底层控制层，替代原版的 Underlying_Operations.py。

主要改进：
  - 截图：使用 MaaFramework 内置 minicap，无需 adb pull，速度更快
  - 点击/滑动：使用 maatouch，比 adb input 更稳定
  - OCR：使用 MaaFramework 内置 PP-OCRv5 + ONNX Runtime（无需安装 PaddlePaddle）
  - 自动设备发现：Toolkit.find_adb_devices()，无需手动填写端口
  - 像素检测：直接操作 numpy 截图数组，无需落盘再读取

依赖安装：
  pip install MaaFw
"""

import re
import time
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# ── MaaFramework Python 绑定 ─────────────────────────────────────────────────
from maa.toolkit import Toolkit
from maa.controller import AdbController
from maa.resource import Resource
from maa.tasker import Tasker
from maa.context import Context
from maa.custom_recognition import CustomRecognition


# ── 常量 ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PIC_DIR = BASE_DIR / "pic"
PIC_DIR.mkdir(exist_ok=True)


class MaaOperations:
    """
    基于 MaaFramework 的底层操作封装。

    使用方式：
        ops = MaaOperations()
        device_id = ops.select_device()   # 返回 AdbDevice 对象，非字符串
        ops.connect(device_id)
        img = ops.screenshot()            # numpy ndarray, shape=(H,W,3)
    """

    # MuMu12 常见安装路径（仅作 adb_path 的候选，Toolkit 会自动扫描）
    MUMU_ADB_PATHS = [
        r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
        r"C:\Program Files (x86)\Netease\MuMu Player 12\shell\adb.exe",
        r"D:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
        r"D:\MuMu Player 12\shell\adb.exe",
    ]

    def __init__(self):
        # 初始化 Toolkit（必须在 AdbController 之前调用）
        Toolkit.init_option(str(BASE_DIR))
        self.controller: AdbController | None = None
        self._last_screenshot: np.ndarray | None = None

    # ── 设备发现与连接 ────────────────────────────────────────────────────────

    def find_devices(self) -> list:
        """
        通过 MaaFramework 自动扫描 ADB 设备，返回 AdbDevice 列表。
        MuMu 模拟器需要先在模拟器内开启 ADB，或端口为 127.0.0.1:16384。
        """
        devices = Toolkit.find_adb_devices()
        return list(devices)

    def select_device(self):
        """
        交互式选择 ADB 设备，返回选中的 AdbDevice 对象。
        若无设备则返回 False。
        """
        devices = self.find_devices()
        if not devices:
            print("当前无设备连接电脑，请检查设备连接情况！")
            return False
        if len(devices) == 1:
            print(f"当前有一台设备连接: {devices[0].address}")
            return devices[0]
        print("当前存在多台设备，输入数字选择对应设备:")
        for i, d in enumerate(devices):
            print(f"  {i + 1}: {d.address}  ({getattr(d, 'name', '未知型号')})")
        num = int(input()) - 1
        while not (0 <= num < len(devices)):
            print("输入不正确，请重新输入：")
            num = int(input()) - 1
        return devices[num]

    def connect(self, device) -> bool:
        """
        连接到指定 AdbDevice，成功后才能截图、点击等。
        device: select_device() 返回的 AdbDevice 对象。
        """
        self.controller = AdbController(
            adb_path=device.adb_path,
            address=device.address,
            screencap_methods=device.screencap_methods,
            input_methods=device.input_methods,
            config=device.config,
        )
        job = self.controller.post_connection()
        job.wait()
        if job.succeeded():
            print(f"[MAA] 设备已连接: {device.address}")
            return True
        print(f"[MAA] 设备连接失败: {device.address}")
        return False

    # ── 截图（核心改进：内存直传，无需落盘）──────────────────────────────────

    def screenshot(self) -> np.ndarray | None:
        """
        截图并返回 numpy ndarray (H, W, 3)，BGR 格式（与 OpenCV 兼容）。
        同时保存到 pic/screenshot.png 供需要的地方读取。
        """
        if self.controller is None:
            raise RuntimeError("请先调用 connect() 连接设备")
        job = self.controller.post_screencap()
        img = job.wait().get()  # numpy ndarray
        if img is None:
            print("截图失败")
            return None
        self._last_screenshot = img
        # 落盘供兼容读取（PIL 等）
        from PIL import Image
        pil_img = Image.fromarray(img[..., ::-1])  # BGR → RGB
        pil_img.save(str(PIC_DIR / "screenshot.png"))
        timetag = datetime.now().strftime('%H:%M:%S')
        print(f"{timetag} 获取屏幕截图")
        return img

    def get_last_screenshot(self) -> np.ndarray | None:
        """返回上一次截图的 numpy 数组，避免重复截图。"""
        return self._last_screenshot

    def save_reward_pic(self) -> None:
        """保存中奖截图（带时间戳）"""
        img = self.screenshot()
        if img is None:
            return
        timepic = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        from PIL import Image
        pil = Image.fromarray(img[..., ::-1])
        pil.save(str(PIC_DIR / f"{timepic}.png"))
        print(f"中奖了，保存中奖图片 {timepic}.png")

    # ── 像素读取（直接操作 numpy，无需落盘）─────────────────────────────────

    def get_pixel(self, x: int, y: int, img: np.ndarray | None = None):
        """
        读取像素 RGB（非 BGR），与原版 PIL pix[x,y] 行为一致。
        img: 可传入指定帧；默认使用最后一次截图。
        返回 (R, G, B) 元组，或 None。
        """
        frame = img if img is not None else self._last_screenshot
        if frame is None:
            return None
        # frame 是 BGR numpy (H, W, 3)
        bgr = frame[y, x]  # 注意 numpy 索引是 [row=y, col=x]
        return (int(bgr[2]), int(bgr[1]), int(bgr[0]))  # → RGB

    def get_resolution(self) -> tuple[int, int]:
        """
        从最后一次截图中读取分辨率 (width, height)。
        优先使用截图数组；若无截图则用 adb wm size 兜底。
        """
        if self._last_screenshot is not None:
            h, w = self._last_screenshot.shape[:2]
            print(f"设备分辨率：{w}×{h}")
            return w, h
        # 兜底：adb wm size（不依赖 MAA）
        import subprocess
        proc = subprocess.Popen(
            f"{self._find_adb()} shell wm size",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        match = re.search(r'Physical size: (\d+)x(\d+)',
                          out.decode('utf-8', errors='ignore'))
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            print(f"设备分辨率（adb fallback）：{w}×{h}")
            return w, h
        raise ValueError("无法获取设备分辨率")

    def _find_adb(self) -> str:
        """查找 adb 路径（仅供 get_resolution 兜底使用）"""
        import subprocess, os
        try:
            r = subprocess.Popen('adb version', shell=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = r.communicate()
            if b'Android Debug Bridge' in out:
                return 'adb'
        except Exception:
            pass
        for p in self.MUMU_ADB_PATHS:
            if os.path.exists(p):
                return f'"{p}"'
        return 'adb'

    # ── OCR（使用 MaaFramework 内置 PP-OCRv5 + ONNX）────────────────────────

    def _ensure_resource(self) -> Resource:
        """延迟初始化 MAA Resource（含 OCR 模型）"""
        if not hasattr(self, '_resource'):
            self._resource = Resource()
            # OCR 模型位于 MaaFw 包内 bin 目录，Toolkit.init_option 已处理路径
        return self._resource

    def ocr_image(self, img: np.ndarray, roi: tuple | None = None) -> str:
        """
        对 numpy 图像进行 OCR 识别，返回识别到的文字字符串。
        img: BGR numpy ndarray（截图的裁剪区域）
        roi: (x, y, w, h)，若传入则在 img 内再裁剪；默认全图
        """
        if self.controller is None:
            raise RuntimeError("请先 connect()")
        resource = self._ensure_resource()

        class _OcrReco(CustomRecognition):
            _result: str = ""

            def analyze(self_inner, context: Context, argv):
                reco_detail = context.run_recognition(
                    "OcrTask",
                    argv.image,
                    pipeline_override={
                        "OcrTask": {
                            "recognition": "OCR",
                            "roi": list(roi) if roi else [],
                            "expected": ".*",
                            "only_rec": False,
                        }
                    },
                )
                if reco_detail:
                    texts = [item.text for item in reco_detail.filterd_results]
                    self_inner._result = "".join(texts)
                return CustomRecognition.AnalyzeResult(
                    box=(0, 0, 1, 1), detail=self_inner._result)

        reco_instance = _OcrReco()
        resource.register_custom_recognition("_InlineOcr", reco_instance)

        tasker = Tasker()
        tasker.bind(resource, self.controller)
        tasker.post_task("_InlineOcr").wait()
        return reco_instance._result

    def ocr_crop(self, x1: int, y1: int, x2: int, y2: int,
                 img: np.ndarray | None = None) -> str:
        """
        裁剪图像区域并 OCR，返回文字。
        坐标基于基准分辨率（调用方负责比例换算后传入实际像素坐标）。
        """
        frame = img if img is not None else self._last_screenshot
        if frame is None:
            raise RuntimeError("请先截图")
        crop = frame[y1:y2, x1:x2]
        return self.ocr_image(crop)

    # ── 点击与滑动（使用 maatouch，比 adb input 更稳定）────────────────────

    def click(self, x: int, y: int) -> None:
        """点击屏幕坐标 (x, y)"""
        if self.controller is None:
            raise RuntimeError("请先 connect()")
        self.controller.post_click(x, y).wait()

    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration_ms: int = 300) -> None:
        """
        从 (x1,y1) 滑动到 (x2,y2)，duration_ms 为毫秒。
        原版用 steps 参数，MAA 用毫秒，200steps ≈ 300ms。
        """
        if self.controller is None:
            raise RuntimeError("请先 connect()")
        self.controller.post_swipe(x1, y1, x2, y2, duration_ms).wait()

    def press_back(self) -> None:
        """按返回键（keyevent 4）"""
        if self.controller is None:
            raise RuntimeError("请先 connect()")
        self.controller.post_press_key(4).wait()

    def press_enter(self) -> None:
        """按确认键（keyevent 66）"""
        if self.controller is None:
            raise RuntimeError("请先 connect()")
        self.controller.post_press_key(66).wait()

    # ── 工具方法 ──────────────────────────────────────────────────────────────

    def delay(self, seconds: float = 1.0) -> None:
        time.sleep(seconds)

    def random_delay(self, min_seconds: int = 1, max_seconds: int = 100) -> None:
        secs = random.randint(min_seconds, max_seconds)
        print(f"随机等待 {secs} 秒")
        self.delay(secs)

    def get_current_hour(self) -> int:
        h = datetime.now().hour
        print(f"当前时间 {h} 点")
        return h

    def get_battery_level(self) -> int:
        """通过 adb 读取电量（MAA 未封装，回退到 subprocess）"""
        import subprocess
        proc = subprocess.Popen(
            f"{self._find_adb()} shell dumpsys battery",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        match = re.search(r'level:\s*(\d+)',
                          out.decode('utf-8', errors='ignore'))
        if not match:
            print("无法获取电量，返回默认值 100")
            return 100
        level = int(match.group(1))
        print(f"设备当前电量 {level}%")
        return level

    def check_countdown(self, last_time: str = '') -> tuple | bool:
        """
        将 OCR 识别到的倒计时字符串（如 '1230'）转为秒数和到期时间戳。
        返回 (total_seconds, future_timestamp) 或 False。
        """
        try:
            digits = ''.join(c for c in last_time if c.isdigit())
            if len(digits) == 4:
                minutes = int(digits[:2])
                seconds = int(digits[2:])
            else:
                print("时间格式异常")
                return False
            total = minutes * 60 + seconds
            print(f"剩余总秒数：{total}")
            if total > 900:
                total = 890
            future_ts = (datetime.now() + timedelta(seconds=total)).timestamp()
            formatted = datetime.fromtimestamp(future_ts).strftime('%Y-%m-%d %H:%M:%S')
            print(f"预计开奖时间：{formatted}")
            return total, future_ts
        except ValueError:
            print("输入的字符串不是有效的时间格式")
            return False
