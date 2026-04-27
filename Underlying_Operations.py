from paddleocr import PaddleOCR
import subprocess
from datetime import datetime, timedelta
import os
import time
from PIL import Image, ImageFilter
import numpy as np
import logging
import re
import random

class underlying_operations:
    """底层操作类"""

    # MuMu模拟器12 常见 adb.exe 路径（按优先级排列）
    MUMU_ADB_PATHS = [
        r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
        r"C:\Program Files (x86)\Netease\MuMu Player 12\shell\adb.exe",
        r"D:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
        r"D:\MuMu Player 12\shell\adb.exe",
    ]
    # MuMu12 默认 TCP 端口（多开时依次为 16384, 16386, 16388...）
    MUMU_ADB_HOST = "127.0.0.1:16384"

    def __init__(self):
        self.ocr = PaddleOCR()
        logging.disable(logging.DEBUG)
        logging.disable(logging.WARNING)
        self.adb = self._find_adb()
        self._connect_mumu()

    def _find_adb(self):
        """自动探测可用的 adb 命令或路径"""
        # 1. 优先检查系统 PATH 里是否有 adb
        try:
            result = subprocess.Popen('adb version', shell=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = result.communicate()
            if b'Android Debug Bridge' in out:
                print("[ADB] 使用系统 PATH 中的 adb")
                return 'adb'
        except Exception:
            pass
        # 2. 尝试 MuMu 安装目录中的 adb.exe
        for path in self.MUMU_ADB_PATHS:
            if os.path.exists(path):
                print(f"[ADB] 使用 MuMu 自带 adb: {path}")
                return f'"{path}"'
        # 3. 都找不到，给出提示但不崩溃
        print("[ADB] ⚠️  未找到 adb.exe，请将 adb 所在目录加入系统 PATH，")
        print("         或修改 MUMU_ADB_PATHS 列表填入正确路径。")
        return 'adb'

    def _connect_mumu(self):
        """尝试连接 MuMu 模拟器（TCP 模式）"""
        try:
            result = subprocess.Popen(
                f'{self.adb} connect {self.MUMU_ADB_HOST}',
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, _ = result.communicate()
            out = out.decode('utf-8', errors='ignore').strip()
            if 'connected' in out or 'already connected' in out:
                print(f"[ADB] MuMu 模拟器已连接: {self.MUMU_ADB_HOST}")
            else:
                print(f"[ADB] MuMu 连接结果: {out}（若使用真机可忽略）")
        except Exception as e:
            print(f"[ADB] 连接 MuMu 时出错: {e}")

    def select_device(self):
        """选择需要连接的设备"""
        proc = subprocess.Popen(
            '{} devices'.format(self.adb), shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        totalstring = out.decode('utf-8', errors='ignore')
        pattern = r'(\b(?:[0-9]{1,3}(?:\.[0-9]{1,3}){3}(?::[0-9]+)?|[A-Za-z0-9]{8,})\b)\s*device\b'
        devicelist = re.findall(pattern, totalstring)
        devicenum = len(devicelist)
        if devicenum == 0:
            print("当前无设备连接电脑，请检查设备连接情况！")
            return False
        elif devicenum == 1:
            print("当前有一台设备连接，编号:{}.".format(devicelist[0]))
            return devicelist[0]
        else:
            print("当前存在多台设备连接！输入数字选择对应设备:")
            dictdevice = {}
            for i in range(devicenum):
                proc2 = subprocess.Popen(
                    '{} -s {} shell getprop ro.product.device'.format(self.adb, devicelist[i]),
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                modeout, _ = proc2.communicate()
                modestring = modeout.decode('utf-8', errors='ignore').strip()
                print("{}:{}---{}".format(i + 1, devicelist[i], modestring))
                dictdevice[i + 1] = devicelist[i]
            num = int(input())
            while num not in dictdevice:
                print('输入不正确，请重新输入：')
                num = int(input())
            return dictdevice[num]

    def get_screenshot(self, device_id, path='pic'):
        """截图，adb命令需要约2秒"""
        if path == 'pic':
            save_path = os.path.dirname(os.path.abspath(__file__)) + '/pic'
        else:
            save_path = os.path.dirname(os.path.abspath(__file__)) + '/target_pic'
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        try:
            subprocess.Popen(
                '{} -s {} shell screencap -p /sdcard/DCIM/screenshot.png'.format(self.adb, device_id)
            ).wait()
            subprocess.Popen(
                '{} -s {} pull /sdcard/DCIM/screenshot.png {}'.format(self.adb, device_id, save_path),
                stdout=subprocess.PIPE
            ).wait()
            timetag = datetime.now().strftime('%H:%M:%S')
            print("{} 获取屏幕截图".format(timetag))
            return True
        except Exception as e:
            print("截图失败，尝试备用方案: {}".format(e))
            try:
                subprocess.Popen(
                    '{} -s {} shell screencap -p /sdcard/DCIM/screenshot1.png'.format(self.adb, device_id)
                ).wait()
                subprocess.Popen(
                    '{} -s {} shell mv /sdcard/DCIM/screenshot1.png /sdcard/DCIM/screenshot.png'.format(
                        self.adb, device_id)
                ).wait()
                # 修复原始bug：此处应传入 device_id，而非 path
                return self.get_screenshot(device_id, path)
            except Exception as e2:
                print("备用截图方案也失败: {}".format(e2))
                return False

    def get_current_hour(self):
        """获取当前的时间小时数"""
        time_hour = datetime.now().strftime('%H')
        print("当前时间{}点".format(time_hour))
        return int(time_hour)

    def click_confirm(self, device_id):
        """点击确认键"""
        os.system("{} -s {} shell input keyevent 66".format(self.adb, device_id))
        print("点击确认键")

    def click_back(self, device_id):
        """点击返回键"""
        os.system("{} -s {} shell input keyevent 4".format(self.adb, device_id))
        print("点击返回键")

    def get_ballery_level(self, device_id):
        """获取设备电量信息"""
        battery_info = subprocess.Popen(
            "{} -s {} shell dumpsys battery".format(self.adb, device_id),
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = battery_info.communicate()
        battery_info_string = out.decode('utf-8', errors='ignore')
        location = re.search(r'level:\s*(\d+)', battery_info_string)
        if not location:
            print("无法获取电量信息，返回默认值100")
            return 100
        battery_level = int(location.group(1))
        print("设备当前电量为{}".format(battery_level))
        return battery_level

    def get_device_resolution(self, device_id):
        """获取设备分辨率"""
        resolution_info = subprocess.Popen(
            "{} -s {} shell wm size".format(self.adb, device_id),
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = resolution_info.communicate()
        resolution_info_string = out.decode('utf-8', errors='ignore')
        match = re.search(r'Physical size: (\d+)x(\d+)', resolution_info_string)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            print("设备分辨率为：{}*{}".format(width, height))
            return width, height
        raise ValueError("无法从 adb 输出中解析分辨率，输出内容：{}".format(resolution_info_string))

    def save_reward_pic(self, device_id):
        path = os.path.dirname(os.path.abspath(__file__)) + '/pic'
        timepic = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        subprocess.Popen(
            '{} -s {} shell screencap -p /sdcard/DCIM/screenshot.png'.format(self.adb, device_id)
        ).wait()
        subprocess.Popen(
            '{} -s {} pull /sdcard/DCIM/screenshot.png {}/{}.png'.format(self.adb, device_id, path, timepic),
            stdout=subprocess.PIPE
        ).wait()
        subprocess.Popen(
            '{} -s {} shell rm /sdcard/DCIM/screenshot.png'.format(self.adb, device_id)
        ).wait()
        print("中奖了，点击领奖，保存中奖图片{}.png".format(timepic))

    def cut_pic(self, left_up=(0, 63), right_down=(1080, 1620), target='', name=''):
        '''裁剪图片，获取需要的区域小图片方便识别'''
        base = os.path.dirname(os.path.abspath(__file__))
        if target == '' or target is False:
            path = base + '/pic'
            pic1_path = path + '/screenshot.png'
            pic = Image.open(pic1_path)
            cut_pic_path = path + ('/' + name + '.png' if name else '/cut.png')
            pic.crop((left_up[0], left_up[1], right_down[0], right_down[1])).save(cut_pic_path)
            return True
        path_target = base + '/pic/' + target
        pic1_path = path_target + '/screenshot.png'
        pic = Image.open(pic1_path)
        cut_pic_path = path_target + ('/' + name + '.png' if name else '/cut.png')
        pic.crop((left_up[0], left_up[1], right_down[0], right_down[1])).save(cut_pic_path)

    def analyse_pic_word(self, picname='', change_color=0):
        """识别图像中的文字, change_color=1或2为不同的二值化模式，其他不做处理"""
        path = os.path.dirname(os.path.abspath(__file__)) + '/pic'
        if picname == '':
            pic = path + '/cut.png'
        else:
            pic = path + '/' + picname + '.png'
        img = Image.open(pic)
        img = img.convert('L')  # 转换为灰度图
        if change_color == 1:
            img = img.point(lambda x: 0 if x < 128 else 255)  # 二值化
        elif change_color == 2:
            img = img.point(lambda x: 0 if x < 180 else 255)  # 二值化
        img_np = np.array(img)  # 将 Image 对象转换为 numpy 数组
        result = self.ocr.ocr(img_np)
        if result == [None]:
            return ''
        return self.extract_ocr_content(result)

    def extract_ocr_content(self, content=None):
        """对OCR识别到的内容进行取值和拼接，变成完整的一段内容"""
        if content is None:
            return ''
        ocr_result = content
        extracted_content = []
        for item in ocr_result[0]:  # item 的结构为 [位置信息, (识别内容, 置信度)]
            extracted_content.append(item[1][0])
        contains = ''.join(context for context in extracted_content if context)
        return contains

    def delay(self, seconds=1):
        time.sleep(seconds)

    def random_delay(self, min_seconds=1, max_seconds=100):
        """等待随机的时长"""
        random_wait_seconds = random.randint(min_seconds, max_seconds)
        print("随机等待{}秒.".format(random_wait_seconds))
        self.delay(random_wait_seconds)

    def check_countdown(self, last_time=''):
        """对倒计时时间进行转化，变成秒存储"""
        try:
            last_time = ''.join([char for char in last_time if char.isdigit()])
            if len(last_time) == 4:
                # minutes, seconds = map(int, last_time.split(':'))
                minutes = int(last_time[:2])
                seconds = int(last_time[2:])
            else:
                print("时间格式异常")
                return False
            # 转换为总秒数
            total_seconds = minutes * 60 + seconds
            print("剩余总秒数：", total_seconds)
            if total_seconds > 900:  # 如果识别到的分钟大于15，说明识别异常了，按15分钟处理
                total_seconds = 890
            # datetime.strptime(in_time, '%H:%M')
            # time_obj = datetime.strptime(in_time, '%H:%M')
            # print("转换后的时间格式：", time_obj)
            now = datetime.now()
            future_time = now + timedelta(seconds=total_seconds)
            # 将到期时间转换为时间戳
            future_timestamp = future_time.timestamp()
            future_datetime = datetime.fromtimestamp(future_timestamp)
            # 将datetime对象格式化为通常的时间格式
            formatted_future_time = future_datetime.strftime('%Y-%m-%d %H:%M:%S')
            print("预计开奖时间：", formatted_future_time)
            return total_seconds, future_timestamp
        except ValueError:
            print("输入的字符串不是有效的时间格式")
            return False

    def swipe(self, device_id, left_up_x=0, left_up_y=0, right_down_x=1080, right_down_y=1500, steps=200):
        """划动屏幕"""
        os.system("{} -s {} shell input swipe {} {} {} {} {}".format(
            self.adb, device_id, left_up_x, left_up_y, right_down_x, right_down_y, steps))

    def click(self, device_id, x=500, y=500):
        """点击坐标位置"""
        os.system("{} -s {} shell input tap {} {}".format(self.adb, device_id, x, y))
