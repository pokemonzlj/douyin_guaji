"""
douyin_fudai_maa.py
===================
抖音福袋挂机 —— MaaFramework 重构版（替代 douyin_fudai_V3.3.py）

架构变化：
  - 底层控制：改用 maa_controller.MaaOperations
  - 截图：MaaFramework 内置 minicap（内存直传，无需 adb pull）
  - OCR：内置 PP-OCRv5 + ONNX Runtime（无需 PaddlePaddle）
  - 像素检测：直接操作 numpy 截图数组，无落盘开销
  - 点击/滑动：maatouch，比 adb input 更稳定

使用方式：
  from douyin_fudai_maa import FudaiAnalyse
  fa = FudaiAnalyse()
  fa.fudai_choujiang(needswitch=True, wait_minutes=5)
"""

import os
import sys
import time
import atexit
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image

from maa_controller import MaaOperations

# ── 常量 ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PIC_DIR = BASE_DIR / "pic"
PIC_DIR.mkdir(exist_ok=True)

# 基准分辨率（所有坐标均以此为基准）
BASE_W = 1080
BASE_H = 2400


# ── Tee（同时写日志文件和控制台）────────────────────────────────────────────
class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


# ── 主类 ──────────────────────────────────────────────────────────────────────
class FudaiAnalyse:
    """
    福袋抽奖分析与操控类（MaaFramework 版）

    构造后调用 fudai_choujiang() 即可启动挂机。
    """

    def __init__(self):
        # 日志
        timepic = datetime.now().strftime('%Y-%m-%d-%H-%M')
        log_file = open(timepic + '.log', 'w', encoding='utf-8')
        sys.stdout = Tee(sys.stdout, log_file)
        atexit.register(log_file.close)

        # 运行时状态
        self.y_pianyi: int = 0      # y 轴偏移（刘海屏/模拟器适配）
        self.rx: int = BASE_W       # 实际宽度（connect 后由截图自动填充）
        self.ry: int = BASE_H       # 实际高度
        self.last_find_fudai_time: float = 0.0
        self.last_refresh_zhibo_list_time: float = 0.0

        # 底层操作
        self.ops = MaaOperations()

        # 配置
        self.config_path = str(BASE_DIR / "config.json")
        self.contains_not_want: list[str] = []
        self.contains_want: list[str] = []
        self._load_config()

    # ── 配置加载 ──────────────────────────────────────────────────────────────

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                self.contains_not_want = cfg.get("contains_not_want", [])
                self.contains_want = cfg.get("contains_want", [])

    # ── 坐标换算（基准 → 实际）───────────────────────────────────────────────

    def _x(self, bx: int) -> int:
        """基准 x 坐标 → 实际像素 x"""
        return bx * self.rx // BASE_W

    def _y(self, by: int, offset: int = 0) -> int:
        """基准 y 坐标 → 实际像素 y（可叠加 y_pianyi 偏移）"""
        return by * self.ry // BASE_H + offset

    # ── 截图与像素检测 ────────────────────────────────────────────────────────

    def _screenshot(self) -> np.ndarray | None:
        """截图并更新 rx/ry"""
        img = self.ops.screenshot()
        if img is not None:
            self.ry, self.rx = img.shape[:2]
        return img

    def _pixel(self, bx: int, by: int,
               y_off: int = 0,
               img: np.ndarray | None = None):
        """
        读取基准坐标 (bx, by) 处的 RGB 像素。
        y_off 额外偏移（用于 y_pianyi）。
        """
        return self.ops.get_pixel(
            self._x(bx),
            self._y(by) + y_off,
            img=img
        )

    # ── 点击与滑动（坐标均为基准值）─────────────────────────────────────────

    def click(self, bx: int, by: int, y_off: int = 0):
        """点击基准坐标"""
        self.ops.click(self._x(bx), self._y(by) + y_off)

    def swipe(self, bx1: int, by1: int, bx2: int, by2: int,
              duration_ms: int = 300):
        """滑动基准坐标"""
        self.ops.swipe(
            self._x(bx1), self._y(by1),
            self._x(bx2), self._y(by2),
            duration_ms
        )

    # ── OCR 辅助（基准坐标裁剪后识别）──────────────────────────────────────

    def _ocr(self, bx1: int, by1: int, bx2: int, by2: int,
             y_off: int = 0,
             img: np.ndarray | None = None) -> str:
        """对基准坐标区域做 OCR，返回文字字符串。"""
        frame = img if img is not None else self.ops.get_last_screenshot()
        if frame is None:
            self._screenshot()
            frame = self.ops.get_last_screenshot()
        x1 = self._x(bx1)
        y1 = self._y(by1) + y_off
        x2 = self._x(bx2)
        y2 = self._y(by2) + y_off
        # 直接 numpy 裁剪 → OCR
        return self.ops.ocr_crop(x1, y1, x2, y2, img=frame)

    # ═══════════════════════════════════════════════════════════════════════════
    # 业务逻辑（与 V3.3 对齐，仅底层调用替换）
    # ═══════════════════════════════════════════════════════════════════════════

    # ── 人机验证 ──────────────────────────────────────────────────────────────

    def _check_robot(self) -> int:
        """
        检测人机校验类型。
        返回 1=滑块, 2=点击图片, 3=人脸, 0=无
        """
        result = self._ocr(130, 790, 680, 870)
        if "验证" in result:
            print("存在滑动图片人机校验")
            return 1
        if "形状相同" in result:
            print("存在点击图片人机校验")
            return 2
        result2 = self._ocr(340, 1415, 700, 1518)
        if "开始检测" in result2:
            print("存在人脸识别人机校验")
            return 3
        return 0

    def _check_robot_slide_distance(self) -> int | None:
        """计算滑块验证码的滑动距离（像素），返回 None 表示未找到"""
        img = self.ops.get_last_screenshot()
        if img is None:
            return None
        x1, y1 = self._x(143), self._y(884)
        x2, y2 = self._x(936), self._y(1380)
        crop = img[y1:y2, x1:x2]

        h, w = crop.shape[:2]
        start_x = start_y = None

        # 找白色像素（滑块）
        for row in range(20, h - 30):
            for col in range(5, w - 40):
                r, g, b = int(crop[row, col, 2]), int(crop[row, col, 1]), int(crop[row, col, 0])
                if r > 240 and g > 240 and b > 240:
                    start_x, start_y = col, row
                    break
            if start_x is not None:
                break

        if start_x is None:
            print("未找到滑块起始白色像素，无法计算距离")
            return None

        # 找缺口（深色像素）
        for col in range(start_x, w - 40):
            r = int(crop[start_y, col, 2])
            g = int(crop[start_y, col, 1])
            b = int(crop[start_y, col, 0])
            if r < 50 and g < 55 and b < 85 and (r + g + b) < 150:
                dist = col - start_x
                print(f"需要滑动的距离为 {dist}")
                return dist

        print("未找到缺口深色像素，无法计算距离")
        return None

    def _deal_robot_slide(self, distance=400):
        """处理滑块验证码"""
        target_x = (222 + (distance or 400)) * self.rx // BASE_W
        self.swipe(222, 1444, target_x * BASE_W // self.rx, 1444, 300)
        print(f"滑轨滑动 {distance} 距离解锁人机验证")
        self.ops.delay(1)

    def deal_robot(self):
        """统一处理人机校验（最多尝试 10 次）"""
        for attempt in range(10):
            robot_type = self._check_robot()
            if robot_type == 1:
                dist = self._check_robot_slide_distance()
                self._deal_robot_slide(dist)
                self.ops.delay(10)
                self._screenshot()
            elif robot_type == 2:
                print("无法处理点击图片验证，关闭弹窗，等待 30 分钟")
                self.click(910, 800)
                self.ops.delay(1800)
                return
            elif robot_type == 3:
                print("无法处理人脸识别，点击返回，等待 30 分钟")
                self.ops.press_back()
                self.ops.delay(2)
                self.ops.press_back()
                self.ops.delay(1800)
                return
            else:
                return  # 无人机校验，正常退出
        print("超过 10 次仍无法处理人机校验，等待 30 分钟")
        self.click(910, 800)
        self.ops.delay(1800)

    # ── 直播间状态检测 ────────────────────────────────────────────────────────

    def _check_in_follow_list(self) -> bool:
        text = self._ocr(244, 130, 875, 220)
        if "关注" in text:
            print("当前界面在用户关注列表")
            return True
        return False

    def _check_in_zhibo_list(self) -> bool:
        text = self._ocr(400, 145, 675, 230)
        if "正在直播" in text:
            print("当前界面已经在关注的直播间列表")
            return True
        return False

    def _check_zhibo_closed(self) -> bool:
        text = self._ocr(350, 100, 740, 300)
        if "已结束" in text:
            print("当前直播间已关闭")
            return True
        print("当前直播间正常进行中")
        return False

    def _check_zhibo_popup(self) -> bool:
        """判断是否弹出了节假日红包弹窗"""
        text = self._ocr(425, 880, 660, 960)
        if "最高金额" in text:
            print("直播间有红包弹窗")
            return True
        return False

    def _check_stop_charging(self) -> bool:
        text = self._ocr(225, 1951, 865, 2051)
        if "充电" in text:
            print("设备弹出停止充电提醒！")
            return True
        return False

    def _check_zhibo_list_have_zhibo(self) -> bool:
        """直播列表是否有直播内容（像素检测）"""
        img = self._screenshot()
        if img is None:
            return False
        px = self.ops.get_pixel(self._x(290), self._y(490), img=img)
        if px and px[0] == 255 and px[1] == 255 and px[2] == 255:
            print("直播间列表为空")
            return False
        print("直播间列表存在直播内容")
        return True

    # ── 福袋图标检测（核心，像素扫描）──────────────────────────────────────

    def check_have_fudai(self) -> int | bool:
        """
        扫描直播间顶部区域，寻找福袋图标。
        返回找到的基准 x 坐标（41~409），未找到返回 False。
        """
        for loop in range(6):
            self.ops.delay(1.5)
            img = self._screenshot()
            if img is None:
                continue
            scan_y = self._y(403) + self.y_pianyi
            if scan_y < 0 or scan_y >= img.shape[0]:
                continue
            for bx in range(41, 410):
                px = self._x(bx)
                if px >= img.shape[1]:
                    break
                # BGR → RGB
                b = int(img[scan_y, px, 0])
                g = int(img[scan_y, px, 1])
                r = int(img[scan_y, px, 2])
                if 193 <= r <= 203 and 176 <= g <= 193 and 237 <= b <= 247:
                    self.last_find_fudai_time = time.time()
                    print(f"发现福袋图标，基准 x={bx}")
                    return bx
            if loop >= 4:
                self.deal_robot()
            elif loop < 2 and self._check_zhibo_closed():
                return False
        return False

    # ── 福袋弹窗高度判定（任务数）────────────────────────────────────────────

    def _check_detail_height(self, img: np.ndarray | None = None) -> int:
        """
        判断福袋弹窗需要几个任务：3/2/1/0
        通过检测任务标记的特定蓝色像素。
        """
        frame = img or self.ops.get_last_screenshot()
        if frame is None:
            return 0

        def is_task_color(bx, by):
            px = self.ops.get_pixel(self._x(bx), self._y(by), img=frame)
            if px is None:
                return False
            r, g, b = px
            return 30 <= r <= 38 and 34 <= g <= 40 and 78 <= b <= 84

        check_map = [(3, 883), (2, 983), (1, 1058)]
        for renwu, base_y in check_map:
            for dy in [0, self.y_pianyi, -self.y_pianyi]:
                px_y = self._y(base_y) + dy
                if px_y < 0 or px_y >= frame.shape[0]:
                    continue
                if is_task_color(536, base_y):
                    print(f"参与抽奖有 {renwu} 个任务")
                    return renwu

        if self._check_robot():
            self.deal_robot()
        print("参与抽奖不需要任务")
        return 0

    # ── 福袋内容 & 倒计时 OCR ────────────────────────────────────────────────

    def _get_fudai_content(self, renwu: int = 2) -> tuple[str, str]:
        """
        OCR 识别福袋内容文字和倒计时，返回 (content_text, countdown_text)
        """
        img = self.ops.get_last_screenshot()

        region_map = {
            2: ((390, 1240, 1000, 1460), (390, 1110, 690, 1220)),
            1: ((390, 1300, 1000, 1520), (390, 1180, 690, 1290)),
            3: ((390, 1160, 1000, 1380), (390, 1010, 690, 1120)),
            0: ((390, 1600, 1000, 1820), (390, 1460, 690, 1570)),
        }
        content_reg, countdown_reg = region_map.get(renwu, region_map[0])

        content_text = self._ocr(*content_reg, y_off=self.y_pianyi, img=img)
        print(f"福袋内容：{content_text}")
        countdown_text = self._ocr(*countdown_reg, img=img)
        print(f"倒计时时间：{countdown_text}")
        return content_text, countdown_text

    # ── 福袋内容过滤 ──────────────────────────────────────────────────────────

    def _check_contain(self, contains: str) -> bool:
        """True = 不想要（跳过），False = 想要或无所谓（参与）"""
        if 0 < self.ops.get_current_hour() < 7:
            print("凌晨不对福袋内容做要求")
            return False
        for w in self.contains_want:
            if w in contains:
                print(f"福袋内容是想要的：{w}")
                return False
        for nw in self.contains_not_want:
            if nw in contains:
                print(f"福袋内容不是想要的：{nw}")
                return True
        print("福袋内容未明确是否想要，默认参与")
        return False

    # ── 参与抽奖 ──────────────────────────────────────────────────────────────

    def _attend_choujiang(self) -> bool:
        """点击参与抽奖，返回 True=已参与"""
        for _ in range(2):
            text = self._ocr(306, 2030, 780, 2110)
            print(f"参与抽奖按钮文字：{text}")
            if "参与成功" in text or "还需看播" in text:
                print("已经参与，等待开奖")
                self.click(500, 470)
                return True
            elif "无法参与" in text or "时长不足" in text:
                print("条件不满足，无法参与")
                self.click(500, 470)
                return False
            elif "评论" in text or "参与抽奖" in text or "开始观看" in text:
                self.click(500, 2060)
                print("点击参与抽奖")
                return True
            elif "加入粉丝团(1钻石)" in text:
                self.click(500, 440)
                self.ops.delay(1)
                return False
            elif "粉丝团" in text:
                self.click(500, 2060)
                self.ops.delay(2)
                self.click(500, 470)
                self.ops.delay(1)
                self._screenshot()
            elif "活动已结束" in text or "开通店铺会员" in text:
                self.click(500, 440)
                if "开通店铺会员" in text:
                    self.ops.press_back()
                    self.ops.delay(1)
                return False
            else:
                print("参与抽奖按钮文字没匹配上")
                return False
        print("参与抽奖多次点击失败")
        return False

    # ── 抽奖结果判定 ──────────────────────────────────────────────────────────

    def _check_lucky_draw_result(self) -> int | bool:
        """
        判定抽奖结果。
        返回 1/2/3 = 未中奖，y坐标整数 = 中奖，False = 无弹窗
        """
        self._screenshot()
        result_text = self._ocr(350, 655, 740, 755)
        if "没有抽中" in result_text:
            no_award_text = self._ocr(340, 1200, 730, 1350)
            if "我知道了" in no_award_text:
                return 1
            elif "领取并使用" in no_award_text:
                return 2
            return 3
        elif "抽中福袋" in result_text:
            print("恭喜中奖了！")
            for y in [1438, 1490]:
                agree_text = self._ocr(280, y - 30, 660, y + 30)
                if "已阅读" in agree_text:
                    return y
        return False

    def _check_reward_notice(self) -> bool:
        self._screenshot()
        text = self._ocr(370, 1350, 680, 1440)
        if "我知道了" in text:
            print("存在奖品领取提醒")
            return True
        return False

    def _check_order_confirm(self) -> bool:
        self._screenshot()
        text = self._ocr(370, 120, 700, 220)
        if "购买成功" in text:
            print("福袋商品下单成功！")
            return True
        return False

    def _get_reward(self, reward_y: int):
        """中奖后领奖流程"""
        self.ops.save_reward_pic()
        self.click(243, reward_y)
        self.ops.delay(1)
        self.click(540, reward_y - 140)
        print("勾选协议，点击领取奖品")
        self.ops.delay(5)
        self.click(886, 2170)
        print("点击下单")
        self.ops.delay(10)
        while self._check_order_confirm():
            self.ops.press_back()
            print("点击回退按钮")
            self.ops.delay(4)
        print("下完单返回到直播间")
        self.ops.delay(4)
        if self._check_lucky_draw_result():
            self.click(540, reward_y + 180)
            self.ops.delay(2)
            self.ops.save_reward_pic()
            self.ops.press_back()
            self.ops.delay(2)
        if self._check_reward_notice():
            print("提醒领奖弹窗未关闭，点击我知道了")
            self.click(540, 1400)
            self.ops.delay(2)
        self.ops.delay(30)
        print("关闭中奖提醒后等待 30 秒")

    # ── 直播间导航 ────────────────────────────────────────────────────────────

    def _reflash_zhibo(self):
        print("下划刷新直播间列表")
        self.swipe(760, 700, 760, 1500)
        self.ops.delay(5)

    def _back_to_zhibo_list(self):
        for _ in range(4):
            self._screenshot()
            if self._check_in_zhibo_list():
                return
            elif self._check_in_follow_list():
                self.click(390, 590)
                print("点击打开直播间列表")
                self.ops.delay(2)
                return
            self.ops.press_back()
            self.ops.delay(2)

    def _into_zhibo_from_list(self):
        while True:
            self._screenshot()
            if self._check_in_zhibo_list():
                current_hour = self.ops.get_current_hour()
                if 2 <= current_hour <= 6:
                    print("等待 10 分钟继续检查")
                    self.ops.delay(600)
                else:
                    self._reflash_zhibo()
                    if current_hour > 7:
                        self.click(290, 490)
                        print("点击打开第一个直播间")
                        break
                    elif self._check_zhibo_list_have_zhibo():
                        self.click(290, 490)
                        print("点击打开第一个直播间")
                        break
                    else:
                        self.ops.press_back()
                        self.ops.delay(3)
                        print("点击退出到关注列表")
            elif self._check_zhibo_popup():
                self.click(540, 1620)
                print("点击关闭红包弹窗")
                self.ops.press_back()
                self.ops.delay(3)
            elif self._check_zhibo_closed():
                self.ops.press_back()
                self.ops.delay(3)
            elif self._check_in_follow_list():
                self.click(390, 590)
                print("点击打开直播间列表")
                self.ops.delay(2)
            else:
                print("当前页面不在直播间，等待 10 分钟")
                self.ops.delay(600)

    # ── 无福袋时间计数 ────────────────────────────────────────────────────────

    def _check_no_fudai_time(self) -> float:
        if 3 <= self.ops.get_current_hour() <= 6:
            self.last_find_fudai_time = 0.0
        elif self.last_find_fudai_time == 0.0:
            self.last_find_fudai_time = time.time()
        if self.last_find_fudai_time > 0:
            wait = round(time.time() - self.last_find_fudai_time, 1)
            if wait > 18000:
                wait = 0
            if wait > 1:
                print(f"距离上次识别到福袋已过去 {wait} 秒")
            return wait
        return 0

    # ── 电量管理 ──────────────────────────────────────────────────────────────

    def _deal_battery(self):
        while self.ops.get_battery_level() < 30:
            print("设备电量较低，退出直播间等待充电")
            self._back_to_zhibo_list()
            self.ops.delay(1800)

    # ═══════════════════════════════════════════════════════════════════════════
    # 主入口
    # ═══════════════════════════════════════════════════════════════════════════

    def fudai_choujiang(
        self,
        y_pianyi: int = 0,
        needswitch: bool = False,
        wait_minutes: int = 15
    ):
        """
        福袋抽奖主循环。

        参数：
            y_pianyi    : y 轴偏移（刘海屏/模拟器分辨率不同时调整）
            needswitch  : 是否在当前直播间无福袋时主动上划切换
            wait_minutes: 倒计时超过此分钟数则跳过该福袋
        """
        self.y_pianyi = y_pianyi
        # 首次截图，读取实际分辨率
        img = self._screenshot()
        if img is not None:
            self.ry, self.rx = img.shape[:2]
            print(f"实际分辨率：{self.rx}×{self.ry}")

        wait_times = 0
        swipe_times = 0
        fudai_not_open_times = 0

        while True:
            self._deal_battery()
            current_hour = self.ops.get_current_hour()

            # 凌晨休眠
            if 2 <= current_hour <= 6:
                self._back_to_zhibo_list()
                print(f"已经凌晨 {current_hour} 点，等待 5 小时")
                self.ops.delay(18000)
                continue

            x = self.check_have_fudai()

            # 30 分钟无福袋 → 重新进入直播间
            if self._check_no_fudai_time() > 1800:
                self.ops.save_reward_pic()
                self._back_to_zhibo_list()
                self._into_zhibo_from_list()
                continue

            if x and swipe_times < 17:
                wait_times = 0
                self.click(x + 45, 430)
                print("点击打开福袋详情")
                self.ops.delay(3)

            elif needswitch:
                if swipe_times < 15 and current_hour > 6:
                    self.swipe(760, 1600, 760, 800, 300)
                    print("直播间无福袋，上划切换直播间")
                    swipe_times += 1
                else:
                    print("直播间刷了 15 个都无福袋，退出到直播列表")
                    self.ops.press_back()
                    self.ops.delay(3)
                    if self._check_in_follow_list():
                        self.click(390, 560)
                    self._into_zhibo_from_list()
                    swipe_times = 0
                self.ops.delay(5)
                continue

            elif self._check_zhibo_closed():
                self._back_to_zhibo_list()
                self._into_zhibo_from_list()
                swipe_times = 0
                self.ops.delay(5)
                continue

            elif self._check_in_zhibo_list():
                self._into_zhibo_from_list()
                swipe_times = 0
                continue

            elif wait_times >= 4:
                if swipe_times < 15:
                    self.swipe(760, 1600, 760, 800, 300)
                    print("直播间等待 4 轮无福袋，上划切换")
                    swipe_times += 1
                    continue
                else:
                    print("上划超过 15 次，退出到直播列表")
                    self._back_to_zhibo_list()
                    self._into_zhibo_from_list()
                    swipe_times = 0
                wait_times = 0
                self.ops.delay(5)
                continue

            else:
                print("直播间暂无福袋，等待 60 秒")
                wait_times += 1
                self.ops.delay(60)
                continue

            # ── 福袋弹窗处理 ──────────────────────────────────────────────
            self._screenshot()
            renwu = self._check_detail_height()
            content_text, time_text = self._get_fudai_content(renwu)

            if self._check_contain(content_text):
                self.click(x + 45, 430)
                print("福袋内容不理想，上划切换")
                self.ops.delay(1)
                self.swipe(760, 1600, 760, 800, 300)
                swipe_times += 1
                self.ops.delay(5)
                continue

            result = self.ops.check_countdown(time_text)
            if result:
                fudai_not_open_times = 0
                lastsecond, future_timestamp = result
            else:
                self._screenshot()
                renwu = self._check_detail_height()
                content_text, time_text = self._get_fudai_content(renwu)
                result = self.ops.check_countdown(time_text)
                if result:
                    fudai_not_open_times = 0
                    lastsecond, future_timestamp = result
                else:
                    fudai_not_open_times += 1
                    self.click(x + 45, 430)
                    print(f"第 {fudai_not_open_times} 次打开福袋异常")
                    if fudai_not_open_times > 10:
                        print("超过 10 次点击福袋无法打开详情，等待 30 分钟")
                        self.ops.delay(1800)
                    self.ops.delay(1)
                    continue

            if lastsecond < 15 and needswitch:
                self.click(x + 45, 430)
                self.swipe(760, 1600, 760, 800, 300)
                print("倒计时小于 15 秒，上划切换")
                swipe_times += 1
                self.ops.delay(5)
                continue

            if needswitch and lastsecond >= 60 * wait_minutes:
                self.click(x + 45, 430)
                self.swipe(760, 1600, 760, 800, 300)
                print(f"倒计时大于 {wait_minutes} 分钟，暂不参与，上划切换")
                swipe_times += 1
                self.ops.delay(5)
                continue

            if not self._attend_choujiang():
                self.swipe(760, 1600, 760, 800, 300)
                print("参与抽奖失败，上划切换")
                swipe_times += 1
                self.ops.delay(5)
                continue

            self.ops.delay(lastsecond + 5)

            have_clicked_no_award = False
            while True:
                check_result = self._check_lucky_draw_result()
                if check_result is False:
                    break
                elif check_result in (1, 2, 3):
                    self.click(540, 1270)
                    print("没有抽中，点击我知道了")
                    self.ops.delay(3)
                    have_clicked_no_award = True
                    if check_result == 2:
                        print("点击了优惠券领取并使用，关闭商品浏览弹窗")
                        self.click(x, 380)
                        self.ops.delay(2)
                else:
                    print("检测到中奖！执行领奖流程")
                    self._get_reward(check_result)
                    break

            if have_clicked_no_award:
                if not needswitch:
                    self.ops.random_delay(180, 450)
                else:
                    self.swipe(760, 1600, 760, 800, 300)
                    print("结束抽奖，上划切换")
                    swipe_times += 1
                    self.ops.delay(5)
                continue

            elif self._check_zhibo_closed():
                print("直播间已关闭，上划切换")
                swipe_times += 1
                self.swipe(760, 1600, 760, 800, 300)
                self.ops.delay(10)
                continue

            elif self._check_in_zhibo_list():
                self._into_zhibo_from_list()
                swipe_times = 0
                continue
