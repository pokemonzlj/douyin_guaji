from paddleocr import PaddleOCR
import subprocess
from datetime import datetime, timedelta
import os
import time
from PIL import Image, ImageFilter
import numpy as np
import logging
import re

class underlying_operations:
    """底层操作类"""
    def __init__(self):
        self.ocr = PaddleOCR()
        logging.disable(logging.DEBUG)
        logging.disable(logging.WARNING)

    def select_device(self):
        """选择需要连接的设备"""
        string = subprocess.Popen('adb devices', shell=True, stdout=subprocess.PIPE)
        totalstring = string.stdout.read()
        totalstring = totalstring.decode('utf-8')
        # print(totalstring)
        pattern = r'(\b(?:[0-9]{1,3}(?:\.[0-9]{1,3}){3}(?::[0-9]+)?|[A-Za-z0-9]{8,})\b)\s*device\b'
        devicelist = re.findall(pattern, totalstring)
        # devicelist = re.compile(r'(\w*)\s*device\b').findall(totalstring)
        devicenum = len(devicelist)
        if devicenum == 0:
            print("当前无设备连接电脑,请检查设备连接情况!")
            return False
        elif devicenum == 1:
            print("当前有一台设备连接，编号:%s." % devicelist[0])
            return devicelist[0]
        else:
            print("当前存在多台设备连接! 输入数字选择对应设备:")
            dictdevice = {}
            for i in range(devicenum):
                string = subprocess.Popen("adb -s %s shell getprop ro.product.device" % devicelist[i], shell=True,
                                          stdout=subprocess.PIPE)
                modestring = string.stdout.read().strip()  # 去除掉自动生成的回车
                print("%s:%s---%s" % (i + 1, devicelist[i], modestring))
                dictdevice[i + 1] = devicelist[i]
            num = input()
            num = int(num)
            while not num in dictdevice.keys():
                print('输入不正确，请重新输入：')
                num = input()
                num = int(num)
            return dictdevice[num]

    def get_screenshot(self, device_id, path='pic'):
        """截图3个adb命令需要2S左右的时间"""
        if path == 'pic':
            path = os.path.dirname(__file__) + '/pic'
        else:
            path = os.path.dirname(__file__) + '/target_pic'
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            subprocess.Popen(
                'adb  -s %s shell screencap -p /sdcard/DCIM/screenshot.png' % device_id).wait()  # -p: save the file as a png
            subprocess.Popen('adb  -s %s pull /sdcard/DCIM/screenshot.png %s ' % (device_id, path),
                             stdout=subprocess.PIPE).wait()
            timetag = datetime.now().strftime('%H:%M:%S')
            print("{} 获取屏幕截图".format(timetag))
            return True
        # subprocess.Popen('adb  -s %s shell rm /sdcard/DCIM/screenshot.png' % device_id).wait()
        except:
            subprocess.Popen(
                'adb  -s %s shell screencap -p /sdcard/DCIM/screenshot1.png' % device_id).wait()
            subprocess.Popen(
                'adb  -s %s shell mv /sdcard/DCIM/screenshot1.png /sdcard/DCIM/screenshot.png' % device_id).wait()
            self.get_screenshot(path)

    def get_current_hour(self):
        """获取当前的时间小时数"""
        time_hour = datetime.now().strftime('%H')
        print("当前时间{}点".format(time_hour))
        return int(time_hour)

    def click_confirm(self, device_id):
        """点击确认键"""
        os.system("adb -s %s shell input keyevent 66" % device_id)
        print("点击确认键")

    def click_back(self, device_id):
        """点击返回键"""
        os.system("adb -s %s shell input keyevent 4" % device_id)
        print("点击返回键")

    def get_ballery_level(self, device_id):
        """获取设备电量信息"""
        battery_info = subprocess.Popen("adb -s %s shell dumpsys battery" % device_id, shell=True,
                                        stdout=subprocess.PIPE)
        battery_info_string = battery_info.stdout.read()
        battery_info_string = bytes.decode(battery_info_string)
        location = re.search('level:', battery_info_string)
        span = location.span()
        start, end = span
        start = end + 1
        for i in range(5):
            end += 1
            if battery_info_string[end] == "\n":
                break
        battery_level = battery_info_string[start:end]  # 第几个到第几个中间接冒号
        battery_level = int(battery_level)
        print("设备当前电量为{}".format(battery_level))
        return battery_level

    def get_device_resolution(self, device_id):
        """获取设备分辨率"""
        resolution_info = subprocess.Popen("adb -s %s shell wm size" % device_id, shell=True,
                                        stdout=subprocess.PIPE)
        resolution_info_string = resolution_info.stdout.read()
        resolution_info_string = bytes.decode(resolution_info_string)
        match = re.search(r'Physical size: (\d+)x(\d+)', resolution_info_string)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            print("设备分辨率为：{}*{}".format(width, height))
            return width, height
        else:
            raise ValueError("Could not find resolution in adb output")
            return False

    def save_reward_pic(self, device_id):
        path = os.path.dirname(__file__) + '/pic'
        timepic = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        subprocess.Popen(
            'adb  -s %s shell screencap -p /sdcard/DCIM/screenshot.png' % (
                device_id)).wait()  # 截图获奖的界面
        subprocess.Popen(
            'adb  -s %s pull /sdcard/DCIM/screenshot.png %s/%s.png ' % (device_id, path, timepic),
            stdout=subprocess.PIPE).wait()
        subprocess.Popen('adb  -s %s shell rm /sdcard/DCIM/screenshot.png' % device_id).wait()
        print("中奖了，点击领奖，保存中奖图片{}.png".format(timepic))

    def cut_pic(self, left_up=(0, 63), right_down=(1080, 1620), target='', name=''):
        '''裁剪图片，获取需要的区域小图片方便识别'''
        if target == '' or target == False:
            path = os.path.dirname(__file__) + '/pic'
            pic1_path = path + '/screenshot.png'
            pic = Image.open(pic1_path)
            if name == '':
                cut_pic_path = path + '/cut.png'
            else:
                cut_pic_path = path + '/' + name + '.png'
            pic.crop((left_up[0], left_up[1], right_down[0], right_down[1])).save(cut_pic_path)
            return True
        path_target = os.path.dirname(__file__) + '/pic/' + target
        pic1_path = path_target + '/screenshot.png'
        pic = Image.open(pic1_path)
        if name == '':
            cut_pic_path = path_target + '/cut.png'
        else:
            cut_pic_path = path_target + '/' + name + '.png'
        pic.crop((left_up[0], left_up[1], right_down[0], right_down[1])).save(cut_pic_path)

    def analyse_pic_word(self, picname='', change_color=0):
        """识别图像中的文字, change_color=1或2为不同的二值化模式，其他不做处理"""
        path = os.path.dirname(__file__) + '/pic'
        if picname == '':
            pic = path + '/cut.png'
        else:
            pic = path + '/' + picname + '.png'
        img = Image.open(pic)
        img = img.convert('L')  # 转换为灰度图
        if change_color == 1:
            img = img.point(lambda x: 0 if x < 128 else 255)  # 二值化
        elif change_color == 2:
            img = img.point(lambda x: 0 if x < 251 else 255)  # 二值化
        # img.save(pic)
        img_np = np.array(img)  # 将 Image 对象转换为 numpy 数组
        result = self.ocr.ocr(img_np)
        if result == [None]:
            return ''
        return self.extract_ocr_content(result)

    def extract_ocr_content(self, content=[]):
        """对OCR识别到的内容进行取值和拼接，变成完整的一段内容"""
        ocr_result = content
        extracted_content = []
        for item in ocr_result[0]:  # item 的结构为 [位置信息, (识别内容, 置信度)]
            extracted_content.append(item[1][0])
        contains = ''.join(context for context in extracted_content if context)
        # print(contain)
        return contains

    def delay(self, seconds=1):
        time.sleep(seconds)

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
        os.system("adb -s {} shell input swipe {} {} {} {} {}".format(device_id, left_up_x, left_up_y, right_down_x, right_down_y, steps))

    def click(self, device_id, x=500, y=500):
        """点击坐标位置"""
        os.system(
            "adb -s {} shell input tap {} {}".format(device_id, x, y))


