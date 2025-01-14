import os
import random
import sys
import time
import re
from PIL import Image, ImageFilter
import pytesseract
import subprocess
from datetime import datetime, timedelta

"""
版本更新日志
V1.0
支持无限循环挂机直播间
1.判断直播间福袋内容是否是想要的，如果不想要则切换直播间
2.直播间倒计时是否还有很久，太久则切换直播间
3.当直播间开奖后，立马切换直播间去别的直播间挂机

V1.1
1.对人机弹窗做判定,适当滑动解锁
2.对截图函数做优化，处理无法截图的情况
3.优化不切换直播间时的逻辑

V1.2
1.判定划动图片验证的人机校验，自动滑动一定距离处理人机验证
2.优化直播间判定逻辑，增加直播停留时间减少被人机的概率
3.增加直播间等待时间的参数，控制直播停留时间减少被人机的概率
4.增加对当前时间的判定，不同时间段对抽奖的内容做不同的处理

V1.3
1.增加直播已结束的判定
2.增加是否在直播列表页面的判定
3.增加回到直播列表重新进入直播的逻辑
4.增加点亮粉丝团抽奖的特殊处理
5.直播提早开奖补充截图内容获取，用于debug

V1.4
1.兼容了一下直播间忽然弹出来618红包弹窗导致页面一直卡在直播间的问题
2.修复进入直播间列表的功能异常的问题
3.优化挂机的时候直播间关闭的判定
4.兼容 同时存在参与条件+参与任务的抽奖
5.增加判断是否在个人中心的关注页面
6.修复领完奖后回到直播间判断不在直播间的问题
7.增加上划切换到直播间直播间已关闭的判断
8.兼容福袋参与抽奖的文案为：参与抽奖

V1.5
1.优化设备未识别的处理逻辑
2.优化图片文件夹不存在创建文件夹的逻辑

V1.6
1.增加日志内容同步输出到log文件中，方便问题排查
2.修复了到凌晨个别直播间提早关闭会导致直播判定卡住的问题
3.调整不切换直播间挂机的逻辑，现在会一直等待到直播间关闭才会切换

V1.7
1.修复单独挂一个直播间，判定直播间已关闭后，不切换直播间的问题
2.增加全局的监控，无论发生什么情况，只要长时间判定为没有福袋，则重置整个挂机流程

V2.0
1.做了不同分辨率手机的兼容，现在不是1080*2400的手机也能挂机了
2.优化了从直播间列表进直播间连刷新2次的问题
3.优化了领奖完成后返回直播间领奖界面依旧没关闭的情况
4.修复了过了凌晨之后直播间一直没有福袋的判定问题

V2.1
1.修复节假日出现的直播红包弹窗一直无法被退出关闭的问题
2.兼容操控通过wifi直连到笔记本电脑上的手机
3.优化弹窗人机验证后，点击返回无法退出验证的情况
4.加入手机电量验证逻辑
5.增加手机电量不足时进入待机模式的逻辑，避免手机直接关机
6.兼容领奖完成后，判定关闭中奖弹窗后还有一个提醒领奖窗口的情况
7.优化凌晨后整个直播列表无直播间导致无法刷新的问题

V2.2
1.优化日志打印逻辑
2.增加点击福袋无法打开，被系统限制参与抽奖的判定逻辑
3.修复在固定直播间挂机会忽然切换直播间的问题
4.修复：没有抽中，点击:我知道了,关闭弹窗，弹窗未关闭的问题
5.修复进入没有加入粉丝团的直播间，无法抽奖但没有切换直播间的问题
6.增加一个抽奖按钮的判定：活动已结束
7.增加了切换到未加入店铺的直播间的抽奖判定
8.修复：中奖后下单，回到直播间依旧存在中奖弹窗提醒关不掉的问题

V2.3
1.兼容任意分辨率的手机，增加横轴对应的分辨率设置
2.优化代码，抽象一部分方法，去除冗余代码
3.修复当直播间列表为空时，点击返回退出到关注中心，判定页面失效，无法回到直播间列表的问题
4.开奖结束后增加一个随机时长等待，减小风控风险
5.补充逻辑处理：直播间因为状态栏高度的不同，导致关闭的判定不同
6.调整挂机逻辑，到后半夜固定时间区间时，不再参与抽奖

V2.4
1.调整偏移值逻辑，填任意正负数都会进行双重匹配，自动确认适宜的偏移值
2.调整长时间无法识别到福袋的逻辑，避免重复打开都是无福袋的直播间导致被风控
3.优化代码，抽象剩余部分方法，去除冗余代码

未来更新
1.获取直播间名字，关联奖品和倒计时，加入判定队列
2.完全自动处理防沉迷验证
3.上划打开的直播间已关闭的逻辑判定
4.增加一定的等待机制，减少被识别为人机的概率
5.兼容直播提早开奖，直播间关闭的判定
6.调整一下凌晨检查直播间列表的数量
7.兼容挂机过程中弹出的：开通特惠省钱卡的弹窗
8.兼容电脑模拟器，支持直接用模拟器挂抖音，无需额外手机
9.增加自动刷视频的功能，增加账号活跃度，提升中奖概率
10.增加直播间互动的功能，增加账号活跃度，提升中奖概率
11.处理异常操作导致弹窗：账号存在风险的验证
"""

class Tee(object):
    """重写print的函数"""

    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


class fudai_analyse:

    def __init__(self):
        self.device_id = 'XXXXXXX'
        self.y_pianyi = 0  # 应用于不同型号手机，图标相对屏幕的高度位置有偏差
        self.resolution_ratio_x = 1080
        self.resolution_ratio_y = 2400
        timepic = datetime.now().strftime('%Y-%m-%d-%H-%M')
        log_file = open(timepic + '.log', 'w')
        sys.stdout = Tee(sys.stdout, log_file)
        self.last_find_fudai_time = 0.0
        self.last_refresh_zhibo_list_time = 0.0

    def get_screenshot(self, path='pic'):
        """截图3个adb命令需要2S左右的时间"""
        if path == 'pic':
            path = os.path.dirname(__file__) + '/pic'
        else:
            path = os.path.dirname(__file__) + '/target_pic'
        if not os.path.exists(path):
            os.makedirs(path)
        try:
            subprocess.Popen(
                'adb  -s %s shell screencap -p /sdcard/DCIM/screenshot.png' % self.device_id).wait()  # -p: save the file as a png
            subprocess.Popen('adb  -s %s pull /sdcard/DCIM/screenshot.png %s ' % (self.device_id, path),
                             stdout=subprocess.PIPE).wait()
            timetag = datetime.now().strftime('%H:%M:%S')
            print("{} 获取屏幕截图".format(timetag))
            return True
        # subprocess.Popen('adb  -s %s shell rm /sdcard/DCIM/screenshot.png' % self.device_id).wait()
        except:
            subprocess.Popen(
                'adb  -s %s shell screencap -p /sdcard/DCIM/screenshot1.png' % self.device_id).wait()
            subprocess.Popen(
                'adb  -s %s shell mv /sdcard/DCIM/screenshot1.png /sdcard/DCIM/screenshot.png' % self.device_id).wait()
            self.get_screenshot(path)

    def get_current_hour(self):
        """获取当前的时间小时数"""
        time_hour = datetime.now().strftime('%H')
        print("当前已经{}点了".format(time_hour))
        return int(time_hour)

    def save_reward_pic(self):
        path = os.path.dirname(__file__) + '/pic'
        timepic = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        subprocess.Popen(
            'adb  -s %s shell screencap -p /sdcard/DCIM/screenshot.png' % (
                self.device_id)).wait()  # 截图获奖的界面
        subprocess.Popen(
            'adb  -s %s pull /sdcard/DCIM/screenshot.png %s/%s.png ' % (self.device_id, path, timepic),
            stdout=subprocess.PIPE).wait()
        subprocess.Popen('adb  -s %s shell rm /sdcard/DCIM/screenshot.png' % self.device_id).wait()
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

    def analyse_pic_word(self, picname='', type=1, change_color=True):
        """识别图像中的文字，type为1识别文字，为2识别时间倒计时"""
        path = os.path.dirname(__file__) + '/pic'
        if picname == '':
            pic = path + '/cut.png'
        else:
            pic = path + '/' + picname + '.png'
        img = Image.open(pic)
        # img = img.resize((img.width * 3, img.height * 3))  # 调整大小
        img = img.convert('L')  # 转换为灰度图
        if change_color:
            img = img.point(lambda x: 0 if x < 128 else 255)  # 二值化
        else:
            img = img.point(lambda x: 0 if x < 251 else 255)  # 二值化
        # img.show() #展示一下处理后的图片
        if os.path.exists('E:/Tesseract-OCR/tesseract.exe'):
            pytesseract.pytesseract.tesseract_cmd = 'E:/Tesseract-OCR/tesseract.exe'
        elif os.path.exists('D:/Tesseract-OCR/tesseract.exe'):
            pytesseract.pytesseract.tesseract_cmd = 'D:/Tesseract-OCR/tesseract.exe'
        elif os.path.exists('F:/Tesseract-OCR/tesseract.exe'):
            pytesseract.pytesseract.tesseract_cmd = 'F:/Tesseract-OCR/tesseract.exe'
        if type != 2:
            text = pytesseract.image_to_string(img, lang='chi_sim')
        # text = pytesseract.image_to_string(img, lang='eng+chi_sim')
        else:
            img = img.filter(ImageFilter.MedianFilter(size=3))  # MedianFilter 将每个像素的值替换为其周围像素值的中值，以减少图像中的噪声。
            text = pytesseract.image_to_string(img, lang='eng')
        if type == 2:
            # print(text)
            # text = ''.join([char for char in text if char.isnumeric() or char == ':'])  #针对时间去噪
            text = ''.join([char for char in text if char.isnumeric()])  # 针对时间去噪
        reformatted_text = text.replace(' ', '').replace('\n', '')
        # print(reformatted_text)
        return reformatted_text

    def deal_robot_pic_change_color(self):
        """处理人机验证的图片"""
        # self.cut_pic((143, 884), (936, 1380), 'save', 'cut')
        path = os.path.dirname(__file__) + '/pic/save'
        pic = path + '/cut5.png'
        img = Image.open(pic)
        img = img.convert('RGB')
        width, height = img.size
        for x in range(5, width - 40):
            for y in range(20, height - 30):
                current_color = img.getpixel((x, y))
                if current_color[0] > 240 and current_color[1] > 240 and current_color[2] > 240:
                    img.putpixel((x, y), (255, 255, 255))  # 白色
                elif current_color[0] < 35 and current_color[1] < 20 and current_color[2] < 20:
                    img.putpixel((x, y), (0, 0, 0))  # 白色
                else:
                    img.putpixel((x, y), (128, 128, 128))  # 黑色
        save_pic = path + '/newimg.png'
        img.save(save_pic)

    def check_robot_pic_distance(self):
        """处理人机验证的图片"""
        self.cut_pic((143 * self.resolution_ratio_x // 1080, 884 * self.resolution_ratio_y // 2400),
                     (936 * self.resolution_ratio_x // 1080, 1380 * self.resolution_ratio_y // 2400), '', 'cut')
        path = os.path.dirname(__file__) + '/pic'
        pic = path + '/cut.png'
        img = Image.open(pic)
        img = img.convert('RGB')
        width, height = img.size
        printed_first_result = False  # 用于记录第一个结果是否已经输出过
        printed_second_result = False  # 用于记录第二个结果是否已经输出过
        for y in range(20, height - 30):
            for x in range(5, width - 40):
                current_color = img.getpixel((x, y))
                if current_color[0] > 240 and current_color[1] > 240 and current_color[2] > 240:
                    if not printed_first_result:  # 确保只输出一次第一个结果
                        print(x, y)
                        printed_first_result = True
                    break
            if printed_first_result:  # 如果已经输出过第一个结果，则退出外层循环
                break
        for x1 in range(x, width - 40):
            current_color = img.getpixel((x1, y))
            if current_color[0] < 50 and current_color[1] < 55 and current_color[2] < 85 and current_color[0] + \
                    current_color[1] + current_color[2] < 150:
                if not printed_second_result:  # 确保只输出一次第二个结果
                    print(x1, y)
                    printed_second_result = True
                print("需要滑动的距离为{}".format(x1 - x))
                return x1 - x

    def deal_robot_pic(self):
        """处理人机验证的图片"""
        # self.cut_pic((143, 884), (936, 1380), 'save', 'cut')
        path = os.path.dirname(__file__) + '/pic/save'
        pic = path + '/cut3.png'
        img = Image.open(pic)
        img = img.convert('RGB')
        width, height = img.size
        threshold = 90  # 阈值，用于判断颜色偏差是否较大
        for x in range(5, width - 40):
            for y in range(20, height - 30):
                # 获取当前像素点的颜色
                if x > 5 and y > 20 and x < width - 40 and y < height - 30:  # 跳过图片边沿的像素点
                    # 获取当前像素点的颜色
                    current_color = img.getpixel((x, y))
                    num_deviant_neighbors = 0
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if 0 <= x + dx < width and 0 <= y + dy < height:  # 确保不超出图像边界
                                neighbor_color = img.getpixel((x + dx, y + dy))
                                if isinstance(neighbor_color, tuple) and len(neighbor_color) == 3:  # 检查颜色格式
                                    neighbor_color = tuple(
                                        min(max(int(c), 0), 255) for c in neighbor_color)  # 确保颜色值在0到255之间
                                    channel_diffs = [abs(a - b) for a, b in zip(current_color, neighbor_color)]
                                    # 如果每个通道的偏差都大于30，则将邻居像素点计数为偏差点
                                    if all(diff > 70 for diff in channel_diffs):
                                        num_deviant_neighbors += 1
                                    # color_diff = sum(abs(a - b) for a, b in zip(current_color, neighbor_color))
                                    # if color_diff > threshold:
                                    #     num_deviant_neighbors += 1
                    # 如果偏差大于阈值的邻居数量大于4，则认为是偏差点
                    if num_deviant_neighbors > 3:
                        img.putpixel((x, y), (255, 255, 255))  # 白色
                    else:
                        img.putpixel((x, y), (0, 0, 0))  # 黑色
        save_pic = path + '/newimg.png'
        img.save(save_pic)

    def check_countdown(self, last_time=''):
        """对倒计时时间进行转化，变成秒存储"""
        try:
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

    def check_detail_height(self):
        """判定福袋弹窗的高度，会因为抽奖所需任务不同稍有区别,分别有不要任务、1/2个任务"""
        path = os.path.dirname(__file__) + '/pic'
        pic1_path = path + '/screenshot.png'
        pic = Image.open(pic1_path)
        # pic_new = Image.open(cut_pic_path)
        pic_new = pic.convert('RGBA')
        pix = pic_new.load()
        if 30 <= pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400][0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400][1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400][2] <= 84:
            print('参与抽奖有3个任务')
            return 3
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400 + self.y_pianyi][
            0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                    1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                    2] <= 84:
            print('参与抽奖有3个任务')
            return 3
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400 - self.y_pianyi][
            0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400 - self.y_pianyi][
                    1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 883 * self.resolution_ratio_y // 2400 - self.y_pianyi][
                    2] <= 84:
            print('参与抽奖有3个任务')
            return 3
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400][0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400][1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400][2] <= 84:
            print('参与抽奖有2个任务')
            return 2
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400 + self.y_pianyi][
            0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                    1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                    2] <= 84:
            print('参与抽奖有2个任务')
            return 2
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400 - self.y_pianyi][
            0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400 - self.y_pianyi][
                    1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 983 * self.resolution_ratio_y // 2400 - self.y_pianyi][
                    2] <= 84:
            print('参与抽奖有2个任务')
            return 2
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400][0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400][1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400][2] <= 84:
            print('参与抽奖有1个任务')
            return 1
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400 + self.y_pianyi][
            0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                    1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                    2] <= 84:
            print('参与抽奖有1个任务')
            return 1
        elif 30 <= pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400 - self.y_pianyi][
            0] <= 38 and 34 <= \
                pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400 - self.y_pianyi][
                    1] <= 40 and 78 <= \
                pix[536 * self.resolution_ratio_x // 1080, 1058 * self.resolution_ratio_y // 2400 - self.y_pianyi][
                    2] <= 84:
            print('参与抽奖有1个任务')
            return 1
        elif self.check_have_robot_analyse():  # 如果打开的弹窗是个人机校验
            self.deal_robot_analyse()
        print('参与抽奖不需要任务')
        return 0

    def check_have_fudai(self):
        """判定直播页面福袋的小图标是否存在"""
        path = os.path.dirname(__file__) + '/pic'
        pic1_path = path + '/screenshot.png'
        loop = 0
        while loop < 6:  # 每3秒识别一次，最多等待18秒
            # start_time = time.time()
            time.sleep(1.5)
            self.get_screenshot()  # 这个函数需要2S
            pic = Image.open(pic1_path)
            # pic_new = Image.open(cut_pic_path)
            pic_new = pic.convert('RGBA')
            pix = pic_new.load()
            for x in range(41, 410):
                if 194 <= \
                        pix[x * self.resolution_ratio_x // 1080, 403 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                            0] <= 200 and 187 <= \
                        pix[x * self.resolution_ratio_x // 1080, 403 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                            1] <= 193 and 241 <= \
                        pix[x * self.resolution_ratio_x // 1080, 403 * self.resolution_ratio_y // 2400 + self.y_pianyi][
                            2] <= 247:  # 判定存在小福袋的图标
                    self.last_find_fudai_time = time.time()
                    return x
            loop += 1
            # end_time = time.time()
            # execution_time = end_time - start_time
            # 打印执行时间
            # print("Execution time: {} seconds".format(execution_time))
            if loop >= 4:
                self.deal_robot_analyse()
            elif loop < 2 and self.check_zhibo_is_closed():
                return False
        return False

    def check_have_robot_analyse(self):
        """检查是否存在人机校验"""
        self.cut_pic((130 * self.resolution_ratio_x // 1080, 790 * self.resolution_ratio_y // 2400),
                     (680 * self.resolution_ratio_x // 1080, 870 * self.resolution_ratio_y // 2400), '',
                     'zhibo_yanzheng')  # 福袋内容详情
        result = self.analyse_pic_word('zhibo_yanzheng', 1)
        if "验证" in result:
            print("存在滑动图片人机校验，需要等待完成验证.")
            return 1
        elif "形状相同" in result:
            print("存在点击图片人机校验，需要等待完成验证.")
            return 2
        return False

    def deal_swipe_robot_analyse(self, distance=400):
        """处理滑动图片的人机验证"""
        if distance:
            targetx = (222 + distance) * self.resolution_ratio_x // 1080
        else:
            targetx = 622 * self.resolution_ratio_x // 1080
        self.swipe(222, 1444, targetx, 1444, 300)
        print("滑轨滑动{}距离解锁人机验证".format(distance))
        time.sleep(1)

    def deal_robot_analyse(self):
        """处理人机校验，包含各种情况"""
        swipe_times = 0
        while swipe_times < 10:
            robot_result = self.check_have_robot_analyse()
            if robot_result == 1:
                distance = self.check_robot_pic_distance()
                self.deal_swipe_robot_analyse(distance)
                time.sleep(10)
                self.get_screenshot()
            elif robot_result == 2:
                print("无法处理图片验证的人机，点击关闭退出验证，等待30分钟")
                self.click(910, 800)  # 点击关闭
                time.sleep(1800)
                break
            else:
                break
            swipe_times += 1
        if swipe_times >= 10:
            print("无法处理图片验证的人机，点击关闭退出验证，等待30分钟")
            self.click(910, 800)  # 点击关闭
            time.sleep(1800)

    def click_confirm(self):
        """点击确认键"""
        os.system("adb -s %s shell input keyevent 66" % self.device_id)
        print("点击确认键")

    def click_back(self):
        """点击返回键"""
        os.system("adb -s %s shell input keyevent 4" % self.device_id)
        print("点击返回键")

    def swipe(self, left_up_x=0, left_up_y=0, right_down_x=1080, right_down_y=1500, steps=200):
        """划动屏幕"""
        left_up_x = left_up_x * self.resolution_ratio_x // 1080
        right_down_x = right_down_x * self.resolution_ratio_x // 1080
        left_up_y = left_up_y * self.resolution_ratio_y // 2400
        right_down_y = right_down_y * self.resolution_ratio_y // 2400
        os.system("adb -s {} shell input swipe {} {} {} {} {}".format(self.device_id, left_up_x, left_up_y, right_down_x, right_down_y, steps))

    def click(self, x=500, y=500):
        """点击坐标位置"""
        x = x * self.resolution_ratio_x // 1080
        y = y * self.resolution_ratio_y // 2400
        os.system(
            "adb -s {} shell input tap {} {}".format(self.device_id, x, y))


    def reflash_zhibo(self):
        """在关注列表，下拉刷新直播间"""
        print("下划刷新直播间列表")
        self.swipe(760, 700, 760, 1500)
        time.sleep(5)

    def check_in_follow_list(self):
        """判断是否界面在我的关注的列表页"""
        # self.cut_pic((244 * self.resolution_ratio_x // 1080, 130 * self.resolution_ratio_y // 2400),
        #              (875 * self.resolution_ratio_x // 1080, 220 * self.resolution_ratio_y // 2400), '',
        #              'zhibo_follow_list')  # 福袋内容详情
        zhibo_list_title = self.analyse_pic_word('zhibo_follow_list', 1)
        print(zhibo_list_title)
        if "关注" in zhibo_list_title:
            print("当前界面在用户关注列表")
            return True
        return False

    def check_in_zhibo_list(self):
        """检查是否当前在直播列表"""
        self.cut_pic((400 * self.resolution_ratio_x // 1080, 145 * self.resolution_ratio_y // 2400),
                     (675 * self.resolution_ratio_x // 1080, 230 * self.resolution_ratio_y // 2400), '',
                     'zhibo_list_title')  # 福袋内容详情
        zhibo_list_title = self.analyse_pic_word('zhibo_list_title', 1)
        if "正在直播" in zhibo_list_title:
            print("当前界面已经在直播间列表")
            return True
        return False

    def check_zhibo_is_closed(self):
        """检查当前直播间是否关闭"""
        self.cut_pic((350 * self.resolution_ratio_x // 1080, 200 * self.resolution_ratio_y // 2400),
                     (740 * self.resolution_ratio_x // 1080, 300 * self.resolution_ratio_y // 2400), '',
                     'zhibo_status')  # 福袋内容详情
        zhibo_list_title = self.analyse_pic_word('zhibo_status', 1)
        # print(zhibo_list_title)
        if "已结束" in zhibo_list_title:
            print("当前直播间已关闭")
            return True
        zhibo_list_title = self.analyse_pic_word('zhibo_status', 1, False)
        # print(zhibo_list_title)
        if "已结束" in zhibo_list_title:
            print("当前直播间已关闭")
            return True
        self.cut_pic((350 * self.resolution_ratio_x // 1080, 100 * self.resolution_ratio_y // 2400),
                     (740 * self.resolution_ratio_x // 1080, 200 * self.resolution_ratio_y // 2400), '',
                     'zhibo_status')  # 福袋内容详情
        zhibo_list_title = self.analyse_pic_word('zhibo_status', 1)
        # print(zhibo_list_title)
        if "已结束" in zhibo_list_title:
            print("当前直播间已关闭")
            return True
        zhibo_list_title = self.analyse_pic_word('zhibo_status', 1, False)
        # print(zhibo_list_title)
        if "已结束" in zhibo_list_title:
            print("当前直播间已关闭")
            return True
        print("当前直播间正常进行中")
        return False

    def check_zhibo_is_closed_guess_whatyoulike(self):
        """检查当前直播间是否关闭-判断猜你喜欢的位置"""
        self.cut_pic((440 * self.resolution_ratio_x // 1080, 1570 * self.resolution_ratio_y // 2400),
                     (640 * self.resolution_ratio_x // 1080, 1640 * self.resolution_ratio_y // 2400), '',
                     'zhibo_status')  # 福袋内容详情
        zhibo_list_title = self.analyse_pic_word('zhibo_status', 1)
        print(zhibo_list_title)
        if "医一" in zhibo_list_title:
            print("当前直播间已关闭")
            return True
        return False

    def back_to_zhibo_list(self):
        """功能初始化，回到直播间列表"""
        click_back_times = 0
        while click_back_times < 4:
            self.get_screenshot()
            if self.check_in_zhibo_list():
                return False
            elif self.check_in_follow_list():
                self.click(390, 590)
                print("点击打开直播间的列表")
                time.sleep(2)
                return False
            self.click_back()
            time.sleep(2)
            click_back_times += 1

    def into_zhibo_from_list(self):
        """从直接列表进入直播间"""
        while True:
            self.get_screenshot()
            if self.check_in_zhibo_list():
                current_hour = self.get_current_hour()
                if 2 <= current_hour <= 6:
                    print("等待10分钟继续检查")
                    time.sleep(600)  # 等待10分钟继续检查
                else:
                    self.reflash_zhibo()  # 刷新直播间列表
                    if current_hour > 7:  # 如果当前时间已经早上8点多了，一定有直播间了
                        self.click(290, 490)  # 点击第一个直播间
                        print("点击打开第一个直播间")
                        break  # 跳出循环，直播间已找到
                    elif self.check_zhibo_list_have_zhibo():  # 如果存在直播间
                        self.click(290, 490)  # 点击第一个直播间
                        print("点击打开第一个直播间")
                        break
                    else:  # 如果直播列表是空的，则退出到关注列表
                        self.click_back()
                        time.sleep(3)
                        print("点击退出到关注列表")
            elif self.check_zhibo_have_popup():
                self.click(540, 1620)
                print("点击关闭红包弹窗")
                self.click_back()
                time.sleep(3)
                print("点击退出直播间")
            elif self.check_zhibo_is_closed():
                self.click_back()
                time.sleep(3)
                print("点击退出直播间")
            elif self.check_in_follow_list():
                self.click(390, 590)
                print("点击打开直播间的列表")
                time.sleep(2)
            else:
                print("当前页面不在直播间")
                time.sleep(600)  # 等待10分钟继续检查
                print("等待10分钟后再检查")

    def check_zhibo_list_have_zhibo(self):
        """检查直播列表是否存在直播的内容"""
        self.get_screenshot()
        path = os.path.dirname(__file__) + '/pic'
        pic1_path = path + '/screenshot.png'
        pic = Image.open(pic1_path)
        # pic_new = Image.open(cut_pic_path)
        pic_new = pic.convert('RGBA')
        pix = pic_new.load()
        if pix[290 * self.resolution_ratio_x // 1080, 490 * self.resolution_ratio_y // 2400][0] == 255 and \
                pix[290 * self.resolution_ratio_x // 1080, 490 * self.resolution_ratio_y // 2400][1] == 255 and \
                pix[290 * self.resolution_ratio_x // 1080, 490 * self.resolution_ratio_y // 2400][2] == 255:
            print('直播间列表为空')
            return False
        print('直播间列表存在直播的内容')
        return True

    def check_zhibo_have_popup(self):
        """判断直播间是否弹出了节假日红包弹窗"""
        self.cut_pic((425 * self.resolution_ratio_x // 1080, 880 * self.resolution_ratio_y // 2400),
                     (660 * self.resolution_ratio_x // 1080, 960 * self.resolution_ratio_y // 2400), '',
                     'zhibo_hongbao')  # 福袋内容详情
        zhibo_list_title = self.analyse_pic_word('zhibo_hongbao', 1)
        if "最高金额" in zhibo_list_title:
            print("直播间有红包弹窗")
            return True
        return False

    def check_no_fudai_time(self):
        """无福袋等待时间检查"""
        if 3 <= self.get_current_hour() <= 6:  # 如果是凌晨3-6点
            self.last_find_fudai_time = 0.00
        elif self.last_find_fudai_time == 0.00 or self.last_find_fudai_time == 0:  # 如果过了不挂机时间，把当前时间赋值给上次找到福袋的时间
            self.last_find_fudai_time = time.time()
        if self.last_find_fudai_time > 0:
            current_time = time.time()
            wait_time = current_time - self.last_find_fudai_time
            wait_time = round(wait_time, 1)
            if wait_time > 18000:
                wait_time = 0
            if wait_time > 1:
                print("距离上一次识别到福袋已经过去{}秒".format(wait_time))
            return wait_time
        return 0

    def get_fudai_contain(self, renwu=2):
        """获取福袋的内容和倒计时"""
        if renwu == 2:  # 如果是2个任务的
            self.cut_pic(
                (390 * self.resolution_ratio_x // 1080, 1240 * self.resolution_ratio_y // 2400 + self.y_pianyi),
                (1000 * self.resolution_ratio_x // 1080, 1410 * self.resolution_ratio_y // 2400 + self.y_pianyi), '',
                'fudai_content')  # 福袋内容详情
            self.cut_pic((397 * self.resolution_ratio_x // 1080, 1120 * self.resolution_ratio_y // 2400),
                         (690 * self.resolution_ratio_x // 1080, 1210 * self.resolution_ratio_y // 2400), '',
                         'fudai_countdown')  # 完整福袋详情倒计时
        elif renwu == 1:  # 如果是1个任务的
            self.cut_pic(
                (390 * self.resolution_ratio_x // 1080, 1300 * self.resolution_ratio_y // 2400 + self.y_pianyi),
                (1000 * self.resolution_ratio_x // 1080, 1470 * self.resolution_ratio_y // 2400 + self.y_pianyi), '',
                'fudai_content')  # 福袋内容详情
            self.cut_pic((390 * self.resolution_ratio_x // 1080, 1190 * self.resolution_ratio_y // 2400),
                         (690 * self.resolution_ratio_x // 1080, 1280 * self.resolution_ratio_y // 2400), '',
                         'fudai_countdown')  # 完整福袋详情倒计时
        elif renwu == 3:  # 如果是3个任务的
            self.cut_pic(
                (390 * self.resolution_ratio_x // 1080, 1160 * self.resolution_ratio_y // 2400 + self.y_pianyi),
                (1000 * self.resolution_ratio_x // 1080, 1340 * self.resolution_ratio_y // 2400 + self.y_pianyi), '',
                'fudai_content')  # 福袋内容详情
            self.cut_pic((390 * self.resolution_ratio_x // 1080, 1020 * self.resolution_ratio_y // 2400),
                         (690 * self.resolution_ratio_x // 1080, 1110 * self.resolution_ratio_y // 2400), '',
                         'fudai_countdown')  # 完整福袋详情倒计时
        else:
            self.cut_pic(
                (390 * self.resolution_ratio_x // 1080, 1600 * self.resolution_ratio_y // 2400 + self.y_pianyi),
                (1000 * self.resolution_ratio_x // 1080, 1760 * self.resolution_ratio_y // 2400 + self.y_pianyi), '',
                'fudai_content')  # 福袋内容详情
            self.cut_pic((390 * self.resolution_ratio_x // 1080, 1470 * self.resolution_ratio_y // 2400),
                         (690 * self.resolution_ratio_x // 1080, 1550 * self.resolution_ratio_y // 2400), '',
                         'fudai_countdown')  # 完整福袋详情倒计时
        fudai_content_text = self.analyse_pic_word('fudai_content', 1)
        print("福袋内容：{}".format(fudai_content_text))
        time_text = self.analyse_pic_word('fudai_countdown', 2)
        print("倒计时时间：{}".format(time_text))
        return fudai_content_text, time_text

    def check_contain(self, contains=''):
        """检查福袋内容是否想要"""
        contains_not_want = []
        contains_want = ["鱼竿", "钓箱", "钓杆"]
        if self.get_current_hour() < 7:
            return False
        for contain in contains_want:
            if contain in contains:
                return False
        for contain in contains_not_want:
            if contain in contains:
                return True
        return False

    def attend_choujiang(self, renwu=1):
        """点击参与抽奖"""
        click_times = 0
        while click_times < 2:
            self.cut_pic((306 * self.resolution_ratio_x // 1080, 2030 * self.resolution_ratio_y // 2400),
                         (780 * self.resolution_ratio_x // 1080, 2110 * self.resolution_ratio_y // 2400), '',
                         "attend_button")  # 参与福袋抽奖的文字
            attend_button_text = self.analyse_pic_word('attend_button', 1)
            print("参与抽奖按钮文字内容：{}".format(attend_button_text))
            if "参与成功" in attend_button_text:  # 如果识别到已经参与抽奖
                print("已经参与，等待开奖")
                self.click(500, 470)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭福袋详情")
                return True
            elif "还需看播" in attend_button_text:  # 如果识别到已经参与抽奖
                print("已经参与，等待看播时间凑齐开奖")
                self.click(500, 470)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭福袋详情")
                return True
            elif "无法参与" in attend_button_text:  # 如果识别到无法参与抽奖
                print("条件不满足，无法参与抽奖")
                self.click(500, 470)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭福袋详情")
                return False
            elif "时长不足" in attend_button_text:  # 如果识别到无法参与抽奖
                print("看播时长不够了，无法参与抽奖")
                self.click(500, 470)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭福袋详情")
                return False
            elif "评论" in attend_button_text:
                self.click(500, 2060)  # 点击参与抽奖
                print("点击参与抽奖")
                return True
            elif "参与抽奖" in attend_button_text:
                self.click(500, 2060)  # 点击参与抽奖
                print("点击参与抽奖")
                return True
            elif "加入粉丝团(1钻石)" in attend_button_text:
                self.click(500, 440)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭支付弹窗")
                time.sleep(1)
                return False
            elif "粉丝团" in attend_button_text:
                self.click(500, 2060)  # 点击加入粉丝团、点亮粉丝团
                time.sleep(2)
                self.click(500, 470) # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭支付弹窗")
                time.sleep(1)
                click_times += 1
                self.get_screenshot()
            elif "活动已结束" in attend_button_text:
                self.click(500, 440)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭福袋详情")
                return False
            elif "开通店铺会员" in attend_button_text:
                self.click_back()
                time.sleep(1)
                self.click(500, 440)  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭入会弹窗")
                time.sleep(1)
                return False
            else:
                print("参与抽奖按钮文字没匹配上")
                click_times = 2
                return False
        print("参与抽奖多次点击失败")
        return False

    def check_have_no_award(self):
        """判定是否未中奖"""
        self.get_screenshot()
        self.cut_pic((357 * self.resolution_ratio_x // 1080, 658 * self.resolution_ratio_y // 2400),
                     (740 * self.resolution_ratio_x // 1080, 750 * self.resolution_ratio_y // 2400), '',
                     "choujiang_result")  # 没有抽中福袋位置
        choujiang_result = self.analyse_pic_word('choujiang_result', 1)
        if "没有抽中" in choujiang_result:
            return True
        return False

    def check_have_reward(self):
        """判断是否中奖"""
        path = os.path.dirname(__file__) + '/pic'
        pic1_path = path + '/screenshot.png'
        pic = Image.open(pic1_path)
        # pic_new = Image.open(cut_pic_path)
        pic_new = pic.convert('RGBA')
        pix = pic_new.load()
        y = 1238
        if 253 <= pix[540 * self.resolution_ratio_x // 1080, 1238 * self.resolution_ratio_y // 2400][0] <= 255 and 43 <= \
                pix[540 * self.resolution_ratio_x // 1080, 1238 * self.resolution_ratio_y // 2400][1] <= 45 and 84 <= \
                pix[540 * self.resolution_ratio_x // 1080, 1238 * self.resolution_ratio_y // 2400][2] <= 86:
            y = 1238
        elif 253 <= pix[540 * self.resolution_ratio_x // 1080, 1290 * self.resolution_ratio_y // 2400][
            0] <= 255 and 43 <= pix[540 * self.resolution_ratio_x // 1080, 1290 * self.resolution_ratio_y // 2400][
            1] <= 45 and 84 <= pix[540 * self.resolution_ratio_x // 1080, 1290 * self.resolution_ratio_y // 2400][
            2] <= 86:
            y = 1290
        self.cut_pic((306 * self.resolution_ratio_x // 1080, (y + 10) * self.resolution_ratio_y // 2400),
                     (780 * self.resolution_ratio_x // 1080, (y + 110) * self.resolution_ratio_y // 2400), '',
                     "get_reward")  # 立即领取奖品
        choujiang_result = self.analyse_pic_word('get_reward', 1)
        if "领取" in choujiang_result:
            print("存在奖品")
            return y + 200  # * self.resolution_ratio_y // 2400
        return False

    def check_have_reward_notice_confirm(self):
        """判断是否有领奖的二次确认提醒"""
        self.get_screenshot()
        self.cut_pic((370 * self.resolution_ratio_x // 1080, 1350 * self.resolution_ratio_y // 2400),
                     (680 * self.resolution_ratio_x // 1080, 1440 * self.resolution_ratio_y // 2400), '',
                     "reward_notice_confirm")  # 提醒领取奖品的弹窗
        choujiang_result = self.analyse_pic_word('reward_notice_confirm', 1)
        if "我知道了" in choujiang_result:
            print("存在奖品领取提醒")
            return True
        return False

    def get_reward(self, reward_y=0):
        """中奖后领奖然后返回"""
        self.save_reward_pic()
        self.click(243, reward_y)  # 勾选协议
        time.sleep(1)
        self.click(540, reward_y - 140)  # 点击领取
        print("勾选协议，点击领取奖品")
        time.sleep(10)
        # self.save_reward_pic()
        self.click(886, 2170)  # 点击下单
        print("点击下单")
        time.sleep(10)
        self.click_back()  # 下完单点击返回直播间
        print("下完单点击返回直播间")
        time.sleep(10)
        if self.check_have_reward():
            print("领奖弹窗未关闭，点击关闭弹窗")
            # self.save_reward_pic()
            self.click(540, reward_y + 180)
            print("点击坐标位置:540 {}关闭领奖弹窗".format((reward_y + 180) * self.resolution_ratio_y // 2400))
            time.sleep(2)
            self.click_back()
            time.sleep(2)
        if self.check_have_reward_notice_confirm():
            print("提醒领奖弹窗未关闭，点击我知道了，关闭弹窗")
            self.click(540, 1400)  # 点击我知道了
            time.sleep(2)
        time.sleep(30)
        print("关闭中奖提醒后等待30S")

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

    def get_ballery_level(self):
        """获取设备电量信息"""
        battery_info = subprocess.Popen("adb -s %s shell dumpsys battery" % self.device_id, shell=True,
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

    def deal_battery_level(self):
        """针对电量不足的情况做处理"""
        while self.get_ballery_level() < 30:
            print("设备电量较低，退出到直播列表，等待电量恢复后继续挂机")
            self.back_to_zhibo_list()
            time.sleep(1800)  # 挂机30分钟

    def fudai_choujiang(self, device_id="", y_pianyi=0, x_resolution=1080, y_resolution=2400, needswitch=False,
                        wait_minutes=15):
        """默认不切换直播间"""
        self.device_id = device_id
        self.y_pianyi = y_pianyi
        self.resolution_ratio_x = x_resolution
        self.resolution_ratio_y = y_resolution
        wait_times = 0  # 当前直播间的等待次数，累计4次没有福袋，则切换直播间
        swipe_times = 0  # 向上滑动的次数,当超出一定值，退出返回直播列表
        fudai_not_open_times = 0  # 无法打开福袋的次数
        while True:
            self.deal_battery_level()
            current_hour = self.get_current_hour()
            if 2 <= current_hour <= 6:
                self.back_to_zhibo_list()
                print("已经凌晨了，退出直播间回到直播列表，等待5个小时")
                time.sleep(18000)
                continue
            x = self.check_have_fudai()
            if self.check_no_fudai_time() > 1800:  # 如果30分钟都没有福袋
                self.save_reward_pic()
                self.back_to_zhibo_list()
                self.into_zhibo_from_list()
                continue
            if x and swipe_times < 17:
                wait_times = 0
                # self.cut_pic((x, 400), (x + 90, 455))  # 通常小福袋的位置
                self.click(x+45, 440)  # 点击默认小福袋的位置
                print("点击打开福袋详情")
                time.sleep(3)
            elif needswitch:  # 如果福袋不存在，且需要切换直播间
                if swipe_times < 15 and self.get_current_hour() > 6:  # 上划次数不到10次，且已经是7点后了，就继续上划
                    self.swipe(760, 1600, 760, 800, 200)
                    print("直播间无福袋，上划切换直播间")
                    swipe_times += 1
                else:  # 如果时间已经是凌晨，没有直播间福袋就整个退出
                    print("直播间刷了15个都无福袋，退出返回直播列表")
                    self.click_back()
                    time.sleep(3)
                    if self.check_in_follow_list():
                        self.click(390, 560)  # 点击直播中
                        print("点击打开直播间列表")
                    self.into_zhibo_from_list()
                    swipe_times = 0  # 滑动次数归0
                time.sleep(5)
                continue
            elif self.check_zhibo_is_closed():  # 如果不切换直播间但直播间已经关闭了
                self.back_to_zhibo_list()
                self.into_zhibo_from_list()
                swipe_times = 0
                time.sleep(5)
                continue
            elif self.check_in_zhibo_list():  # 如果已经退出到直播间列表
                self.into_zhibo_from_list()
                swipe_times = 0  # 滑动次数归0
                continue
            elif wait_times >= 4:  # 如果福袋不存在，且不需要切换直播间，但等待了很久
                if swipe_times < 15:  # 上划次数不到10次，就继续上划
                    self.swipe(760, 1600, 760, 800, 200)
                    print("直播间等待2分钟无福袋，上划切换直播间")
                    swipe_times += 1
                    # time.sleep(5)
                    continue
                else:
                    print("直播间等待2分钟无福袋，退出返回直播列表")
                    self.back_to_zhibo_list()
                    self.into_zhibo_from_list()
                    swipe_times = 0  # 滑动次数归0
                wait_times = 0
                time.sleep(5)
                continue
            else:  # 如果福袋不存在，且不需要切换直播间，且等待轮数不够
                print("直播间暂无福袋，等待60S")
                # wait_times += 1
                time.sleep(60)
                continue
            self.get_screenshot()
            renwu = self.check_detail_height()
            fudai_content_text, time_text = self.get_fudai_contain(renwu)
            if self.check_contain(fudai_content_text) and needswitch:  # 如果福袋内容是不想要的
                self.click(x+45, 470)  # 点击刚才打开小福袋的位置的旁边
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                self.swipe(760, 1600, 760, 800, 200)
                print("直播间福袋内容不理想，上划切换直播间")
                swipe_times += 1
                time.sleep(5)
                continue
            result = self.check_countdown(time_text)
            if result:
                fudai_not_open_times = 0
                lastsecond, future_timestamp = result
            else:  # 如果识别到的倒计时内容不太对，则再判定一次
                self.get_screenshot()
                renwu = self.check_detail_height()
                fudai_content_text, time_text = self.get_fudai_contain(renwu)
                result = self.check_countdown(time_text)
                if result:
                    fudai_not_open_times = 0
                    lastsecond, future_timestamp = result
                else:
                    fudai_not_open_times += 1
                    self.click(x+45, 470)  # 点击刚才打开小福袋的位置的旁边
                    print("第{}次打开福袋异常，点击小福袋旁边位置，坐标({},{})关闭福袋详情".format(fudai_not_open_times, (
                                x + 45) * self.resolution_ratio_x // 1080, 470 * self.resolution_ratio_y // 2400))
                    if fudai_not_open_times > 10:
                        print("超过10次点击福袋无法打开详情，等待30分钟")
                        time.sleep(1800)
                    time.sleep(1)
                    continue
            if lastsecond < 15 and needswitch:  # 如果不到15秒了，就不点了
                self.click(x+45, 470)  # 点击刚才打开小福袋的位置的旁边
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                if needswitch:
                    self.swipe(760, 1600, 760, 800, 200)
                    print("抽奖倒计时时间小于15秒，不参与，上划切换直播间")
                    swipe_times += 1
                time.sleep(5)
                continue
            if needswitch and lastsecond >= 60 * wait_minutes:  # 如果需要切换且倒计时时间大于设定的分钟
                self.click(x+45, 470)  # 点击刚才打开小福袋的位置
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                self.swipe(760, 1600, 760, 800, 200)
                print("抽奖倒计时时间大于{}分钟，暂不参与，上划切换直播间".format(wait_minutes))
                swipe_times += 1
                time.sleep(5)
                continue
            if not self.attend_choujiang(renwu):  # 如果参与抽奖失败
                self.swipe(760, 1600, 760, 800, 200)
                print("参与抽奖失败，上划切换直播间")
                swipe_times += 1
                time.sleep(5)
                continue
            time.sleep(lastsecond)
            no_award_result = self.check_have_no_award()
            if no_award_result:
                self.click(540, 1270)  # 点击我知道了
                print("没有抽中，点击:我知道了,关闭弹窗")
                time.sleep(5)
                no_award_result = self.check_have_no_award()
                if no_award_result:
                    self.click(540, 1270)  # 点击我知道了
                    print("再次点击:我知道了,关闭弹窗")
                    time.sleep(5)
                if not needswitch:
                    random_wait_min = random.randint(3, 8)
                    print("等待{}分钟后继续".format(random_wait_min))
                    time.sleep(60*random_wait_min)
                    continue
                else:
                    self.swipe(760, 1600, 760, 800, 200)
                    print("结束抽奖，上划切换直播间")
                    swipe_times += 1
                    time.sleep(5)
                    continue
            reward_y = self.check_have_reward()
            if reward_y:  # 如果是中奖了
                self.get_reward(reward_y)
                continue
            elif self.check_zhibo_is_closed():  # 如果是直播间关闭了
                print("直播间已关闭，上划切换直播间")
                swipe_times += 1
                self.swipe(760, 1600, 760, 800, 200)
                time.sleep(10)
                continue
            elif self.check_in_zhibo_list():  # 如果已经退出到直播间列表
                self.into_zhibo_from_list()
                swipe_times = 0  # 滑动次数归0
                continue
            self.click(540, 1270)  # 点击我知道了
            print("没有抽中，点击:我知道了,关闭弹窗")
            time.sleep(10)
            continue


if __name__ == '__main__':
    douyin = fudai_analyse()
    douyin.check_in_follow_list()