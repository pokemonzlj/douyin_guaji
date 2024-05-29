import os
import sys
import time
import re
from PIL import Image, ImageFilter
import pytesseract
import subprocess
from datetime import datetime, timedelta


class fudai_analyse:
    """
    版本更新日志
    V1.0
    支持无限循环挂机直播间
    1.判断直播间福袋内容是否是想要的，如果不想要则切换直播间
    2.直播间倒计时是否还有很久，太久则切换直播间
    3.当直播间开奖后，立马切换直播间去别的直播间挂机

    V1.1
    1.对防沉迷弹窗做判定
    3.对截图函数做优化，处理无法截图的情况

    未来更新
    1.获取直播间名字，关联奖品和倒计时，加入判定队列
    2.自动处理防沉迷验证
    """

    def __init__(self):
        self.device_id = 'PBB6ZLEYKZONV86H'
        self.y_pianyi = 0  # 应用于不同型号手机，弹窗的高度位置有偏差
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), 'pic')

    # def __init__(self, device='', y_pianyi=0):
    #     self.device_id = device
    #     self.y_pianyi = y_pianyi   # 应用于不同型号手机，弹窗的高度位置有偏差

    def get_screenshot_new(self, path='pic'):
        if path != 'pic':
            self.screenshot_dir = os.path.join(os.path.dirname(__file__), 'target_pic')
        # 合并命令到一个shell脚本中，但这里我们仍然分开执行
        screenshot_path = os.path.join(self.screenshot_dir, 'screenshot.png')
        # 捕获截图
        subprocess.check_call(['adb', '-s', self.device_id, 'shell', 'screencap', '-p', '/sdcard/DCIM/screenshot.png'])
        # 拉取截图到本地
        subprocess.check_call(['adb', '-s', self.device_id, 'pull', '/sdcard/DCIM/screenshot.png', screenshot_path])
        # 删除设备上的截图
        subprocess.check_call(['adb', '-s', self.device_id, 'shell', 'rm', '/sdcard/DCIM/screenshot.png'])

        timetag = datetime.now().strftime('%H:%M:%S')
        print("{} 获取屏幕截图".format(timetag))

    def get_screenshot(self, path='pic'):
        """截图3个adb命令需要2S左右的时间"""
        if path == 'pic':
            path = os.path.dirname(__file__) + '/pic'
        else:
            path = os.path.dirname(__file__) + '/target_pic'
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

    def cut_pic(self, left_up=(0, 63), right_down=(1080, 1620), target=False, name='', resolution=(1080, 1620)):
        '''裁剪截图，获取需要的小图片方便识别'''
        if not target:
            path = os.path.dirname(__file__) + '/pic'
            pic1_path = path + '/screenshot.png'
            pic = Image.open(pic1_path)
            if name == '':
                cut_pic_path = path + '/cut.png'
            else:
                cut_pic_path = path + '/' + name + '.png'
            pic.crop((left_up[0], left_up[1], right_down[0], right_down[1])).save(cut_pic_path)
        else:
            path_target = os.path.dirname(__file__) + '/target_pic'
            path = path_target
            pic = Image.open(path)
            if name == '':
                cut_pic_path = os.path.dirname(__file__) + '/pic/cut_target.png'
            else:
                cut_pic_path = os.path.dirname(__file__) + '/pic/' + name + '.png'
            pic.crop((left_up[0], left_up[1], right_down[0], right_down[1])).save(cut_pic_path)

    def analyse_pic_word(self, picname='', type=1):
        """识别图像中的文字，type为1识别文字，为2识别时间倒计时"""
        path = os.path.dirname(__file__) + '/pic'
        if picname == '':
            pic = path + '/cut.png'
        else:
            pic = path + '/' + picname + '.png'
        img = Image.open(pic)
        # img = img.resize((img.width * 3, img.height * 3))  # 调整大小
        img = img.convert('L')  # 转换为灰度图
        img = img.point(lambda x: 0 if x < 128 else 255)  # 二值化
        # img.show() #展示一下处理后的图片
        if os.path.exists('E:/Tesseract-OCR/tesseract.exe'):
            pytesseract.pytesseract.tesseract_cmd = 'E:/Tesseract-OCR/tesseract.exe'
        else:
            pytesseract.pytesseract.tesseract_cmd = 'D:/Tesseract-OCR/tesseract.exe'
        if type != 2:
            text = pytesseract.image_to_string(img, lang='chi_sim')
        # text = pytesseract.image_to_string(img, lang='eng+chi_sim')
        else:
            # img = img.resize((img.width * 2, img.height * 2))  # 调整大小
            # new_size = (img.width * 2, img.height * 2)
            # img = img.resize(new_size, Image.LANCZOS)
            # 降噪处理
            img = img.filter(ImageFilter.MedianFilter(size=3))  # MedianFilter 将每个像素的值替换为其周围像素值的中值，以减少图像中的噪声。
            # 在这里，size=3 表示滤波器的尺寸为 3x3，即在每个像素周围取一个 3x3 的区域进行中值计算。
            # img.show()
            text = pytesseract.image_to_string(img, lang='eng')
        if type == 2:
            # print(text)
            # text = ''.join([char for char in text if char.isnumeric() or char == ':'])  #针对时间去噪
            text = ''.join([char for char in text if char.isnumeric()])  # 针对时间去噪
        reformatted_text = text.replace(' ', '').replace('\n', '')
        # print(reformatted_text)
        return reformatted_text

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
        if 30 <= pix[536, 983][0] <= 38 and 34 <= pix[536, 983][1] <= 40 and 78 <= pix[536, 983][2] <= 84:
            print('参与抽奖有2个任务')
            return 2
        elif 30 <= pix[536, 1058][0] <= 38 and 34 <= pix[536, 1058][1] <= 40 and 78 <= pix[536, 1058][2] <= 84:
            print('参与抽奖有1个任务')
            return 1
        print('参与抽奖不需要任务')
        return 0

    def check_have_fudai(self):
        """判定直播页面福袋的小图标是否存在"""
        path = os.path.dirname(__file__) + '/pic'
        pic1_path = path + '/screenshot.png'
        loop = 0
        while loop < 6:  # 每3秒识别一次，最多等待18秒
            start_time = time.time()
            time.sleep(2)
            self.get_screenshot()  # 这个函数需要2S
            pic = Image.open(pic1_path)
            # pic_new = Image.open(cut_pic_path)
            pic_new = pic.convert('RGBA')
            pix = pic_new.load()
            for x in range(41, 410):
                if 194 <= pix[x, 403 + self.y_pianyi][0] <= 200 and 187 <= pix[x, 403 + self.y_pianyi][
                    1] <= 193 and 241 <= pix[x, 403 + self.y_pianyi][2] <= 247:  # 判定存在小福袋的图标
                    return x
            loop += 1
            end_time = time.time()
            execution_time = end_time - start_time
            # 打印执行时间
            # print("Execution time: {} seconds".format(execution_time))
            robot_result = self.check_have_robot_analyse()
            if robot_result == 1:
                self.deal_robot_analyse()
            elif robot_result == 2:
                time.sleep(300)
        return False

    def check_have_robot_analyse(self):
        """检查是否存在人机校验"""
        self.cut_pic((130, 790), (680, 870), False, 'zhibo_yanzheng')  # 福袋内容详情
        result = self.analyse_pic_word('zhibo_yanzheng', 1)
        if "验证" in result:
            print("存在滑动人机校验，需要等待完成验证.")
            return 1
        elif "相同形状" in result:
            print("存在点击图片人机校验，需要等待完成验证.")
            return 2
        return False

    def deal_robot_analyse(self):
        """滑动验证人机"""
        os.system("adb -s %s shell input swipe 222 1444 612 1444 200" % (self.device_id))
        time.sleep(1)

    def reflash_zhibo(self):
        """在关注列表，下拉刷新直播间"""
        print("下划刷新直播间列表")
        os.system("adb -s %s shell input swipe 760 800 760 1600 200" % (self.device_id))
        time.sleep(5)

    def check_zhibo_list(self):
        """检查直播列表是否存在直播的内容"""
        self.get_screenshot()
        path = os.path.dirname(__file__) + '/pic'
        pic1_path = path + '/screenshot.png'
        pic = Image.open(pic1_path)
        # pic_new = Image.open(cut_pic_path)
        pic_new = pic.convert('RGBA')
        pix = pic_new.load()
        if pix[290, 490][0] == 255 and pix[290, 490][1] == 255 and pix[290, 490][2] == 255:
            print('直播间列表为空')
            return False
        print('直播间列表存在直播的内容')
        return True

    def get_fudai_contain(self, renwu=2):
        """获取福袋的内容和倒计时"""
        if renwu == 2:  # 如果是2个任务的
            self.cut_pic((405, 1240 + self.y_pianyi), (1000, 1410 + self.y_pianyi), False, 'fudai_content')  # 福袋内容详情
            self.cut_pic((397, 1120), (690, 1210), False, 'fudai_countdown')  # 完整福袋详情倒计时
        elif renwu == 1:  # 如果是1个任务的
            self.cut_pic((405, 1300 + self.y_pianyi), (1000, 1470 + self.y_pianyi), False, 'fudai_content')  # 福袋内容详情
            self.cut_pic((390, 1190), (690, 1280), False, 'fudai_countdown')  # 完整福袋详情倒计时
        else:
            self.cut_pic((405, 1600 + self.y_pianyi), (1000, 1760 + self.y_pianyi), False, 'fudai_content')  # 福袋内容详情
            self.cut_pic((390, 1470), (690, 1550), False, 'fudai_countdown')  # 完整福袋详情倒计时
        fudai_content_text = self.analyse_pic_word('fudai_content', 1)
        print("福袋内容：{}".format(fudai_content_text))
        time_text = self.analyse_pic_word('fudai_countdown', 2)
        print("倒计时时间：{}".format(time_text))
        return fudai_content_text, time_text

    def check_contain(self, contains=''):
        """检查福袋内容是否想要"""
        contains_to_check = ["鱼护", "钓鱼帽", "水壶", "水杯", "线组", "浮漂", "网头", "硬不", "勺", "饵料", "缠把带",
                             "缠带", "鱼线", "绑钩钳", "诱惑配方", "鱼漂", "黑漂", "子线"]
        for contain in contains_to_check:
            if contain in contains:
                return True
        return False

    def attend_choujiang(self, renwu=1):
        """点击参与抽奖"""
        self.cut_pic((306, 2030), (780, 2110), False, "attend_button")  # 参与福袋抽奖的文字
        attend_button_text = self.analyse_pic_word('attend_button', 1)
        print("参与抽奖按钮文字内容：{}".format(attend_button_text))
        if "参与成功" not in attend_button_text:  # 如果识别到没有参与抽奖
            if "加入粉丝团" in attend_button_text:
                os.system("adb -s %s shell input tap 500 2060" % self.device_id)  # 点击加入粉丝团
                time.sleep(2)
                os.system("adb -s {} shell input tap 500 440".format(self.device_id))  # 点击刚才打开福袋的旁边位置
                print("点击福袋外部，关闭福袋详情")
                # os.system("adb -s %s shell input keyevent 4" % self.device_id) #退出充值的弹窗
                time.sleep(1)
                # self.get_screenshot()
                # self.cut_pic((306, 2040 - self.y_pianyi), (780, 2110 - self.y_pianyi))  # 参与福袋抽奖的文字
                # attend_button_text = self.analyse_pic_word('', 1)
                if renwu == 2:
                    os.system("adb -s %s shell input tap 500 2060" % self.device_id)  # 点击参与抽奖
                    print("点击参与抽奖")
            else:
                os.system("adb -s %s shell input tap 500 2060" % self.device_id)  # 点击参与抽奖
                print("点击参与抽奖")
        else:
            print("已经参与，等待开奖")
            os.system("adb -s {} shell input tap 500 440".format(self.device_id))  # 点击刚才打开福袋的旁边位置
            print("点击福袋外部，关闭福袋详情")
            # os.system("adb -s %s shell input keyevent 4" % self.device_id)

    def select_device(self):
        """选择需要连接的设备"""
        string = subprocess.Popen('adb devices', shell=True, stdout=subprocess.PIPE)
        totalstring = string.stdout.read()
        totalstring = totalstring.decode('utf-8')
        # print(totalstring)
        devicelist = re.compile(r'(\w*)\s*device\b').findall(totalstring)
        devicenum = len(devicelist)
        if devicenum == 0:
            print("当前无设备连接电脑!")
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

    def fudai_choujiang(self, device_id="", y_pianyi=0, needswitch=False):
        """默认不切换直播间"""
        self.device_id = device_id
        self.y_pianyi = y_pianyi
        wait_times = 0  # 当前直播间的等待次数，累计4次没有福袋，则切换直播间
        swipe_times = 0  # 向上滑动的次数,当超出一定值，改为向下滑动
        # option = 'up'
        while True:
            # self.get_screenshot()
            x = self.check_have_fudai()
            if x and swipe_times < 14:
                wait_times = 0
                self.cut_pic((x, 400), (x + 90, 455))  # 通常小福袋的位置
                os.system("adb -s {} shell input tap {} 440".format(self.device_id, x + 45))  # 点击默认小福袋的位置
                print("点击打开福袋详情")
                time.sleep(2)
            elif needswitch:  # 如果福袋不存在，且需要切换直播间
                if swipe_times < 10:  # 上划次数不到10次，就继续上划
                    os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                    print("直播间无福袋，上划切换直播间")
                    swipe_times += 1
                else:
                    print("直播间刷了10个都无福袋，退出返回直播列表")
                    os.system("adb -s %s shell input keyevent 4" % self.device_id)
                    time.sleep(3)
                    while True:
                        self.reflash_zhibo()  # 刷新直播间列表
                        if self.check_zhibo_list():  # 如果存在直播间
                            os.system("adb -s %s shell input tap 290 490" % self.device_id)  # 点击第一个直播间
                            print("点击打开第一个直播间")
                            swipe_times = 0  # 滑动次数归0
                            break  # 跳出循环，直播间已找到
                        else:
                            time.sleep(600)  # 等待10分钟继续检查
                time.sleep(5)
                continue
            elif wait_times >= 4:
                if swipe_times < 10:  # 上划次数不到10次，就继续上划
                    os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                    print("直播间等待2分钟无福袋，上划切换直播间")
                    swipe_times += 1
                    # time.sleep(5)
                    continue
                else:
                    print("直播间等待2分钟无福袋，退出返回直播列表")
                    os.system("adb -s %s shell input keyevent 4" % self.device_id)
                    time.sleep(3)
                    while True:
                        self.reflash_zhibo()  # 刷新直播间列表
                        if self.check_zhibo_list():  # 如果存在直播间
                            os.system("adb -s %s shell input tap 290 490" % self.device_id)  # 点击第一个直播间
                            print("点击打开第一个直播间")
                            # time.sleep(5)
                            swipe_times = 0  # 滑动次数归0
                            break  # 跳出循环，直播间已找到
                        else:
                            time.sleep(600)  # 等待10分钟继续检查
                wait_times = 0
                time.sleep(5)
                continue
            else:
                print("直播间暂无福袋，等待30S")
                wait_times += 1
                time.sleep(30)
                continue
            self.get_screenshot()
            renwu = self.check_detail_height()
            fudai_content_text, time_text = self.get_fudai_contain(renwu)
            if self.check_contain(fudai_content_text) and needswitch:  # 如果福袋内容是不想要的
                os.system("adb -s {} shell input tap {} 440".format(self.device_id, x + 45))  # 点击刚才打开小福袋的位置
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                print("直播间福袋内容不理想，上划切换直播间")
                swipe_times += 1
                time.sleep(5)
                continue
            result = self.check_countdown(time_text)
            if result:
                lastsecond, future_timestamp = result
            else:  # 如果识别到的内容不太对
                os.system("adb -s {} shell input tap {} 440".format(self.device_id, x + 45))  # 点击刚才打开小福袋的位置
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                continue
            if lastsecond < 16:  # 如果不到15秒了，就不点了
                os.system("adb -s {} shell input tap {} 440".format(self.device_id, x + 45))  # 点击刚才打开小福袋的位置
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                print("抽奖倒计时时间小于15秒，不参与，上划切换直播间")
                swipe_times += 1
                time.sleep(5)
                continue
            if needswitch and lastsecond >= 300:  # 如果需要切换且倒计时时间大于5分钟
                os.system("adb -s {} shell input tap {} 440".format(self.device_id, x + 45))  # 点击刚才打开小福袋的位置
                print("点击小福袋位置，关闭福袋详情")
                time.sleep(1)
                os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                print("抽奖倒计时时间大于5分钟，暂不参与，上划切换直播间")
                swipe_times += 1
                time.sleep(5)
                continue
            self.attend_choujiang(renwu)
            time.sleep(lastsecond)
            self.get_screenshot()
            self.cut_pic((357, 674), (740, 750), False, "choujiang_result")  # 没有抽中福袋位置
            choujiang_result = self.analyse_pic_word('choujiang_result', 1)
            if "没有抽中" in choujiang_result:
                os.system("adb -s %s shell input tap 540 1380" % self.device_id)  # 点击我知道了
                print("没有抽中，点击:我知道了,关闭弹窗")
                time.sleep(1)
                if needswitch:
                    os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                    print("结束抽奖，上划切换直播间")
                    swipe_times += 1
                    time.sleep(5)
                    continue
                time.sleep(30)
            else:  # 没弹出没有抽中，可能是直播间关闭，可能是中奖了
                self.cut_pic((306, 1290 - self.y_pianyi), (780, 1410 - self.y_pianyi), False, "get_reward")  # 立即领取奖品
                choujiang_result = self.analyse_pic_word('get_reward', 1)
                if "领取" in choujiang_result:
                    self.save_reward_pic()
                    os.system("adb -s %s shell input tap 243 1495" % self.device_id)  # 勾选协议
                    os.system("adb -s %s shell input tap 540 1350" % self.device_id)  # 点击领取
                    time.sleep(10)
                    os.system("adb -s %s shell input tap 886 2170" % self.device_id)  # 点击下单
                    time.sleep(10)
                    os.system("adb -s %s shell input keyevent 4" % self.device_id)  # 下完单点击返回直播间
                    time.sleep(30)
                    continue
                print("直播间已关闭，上划切换直播间")
                os.system("adb -s %s shell input swipe 760 1600 760 800 200" % (self.device_id))
                time.sleep(10)


if __name__ == '__main__':
    # douyin = fudai_analyse()
    douyin = fudai_analyse()
    douyin.deal_robot_analyse()
    # douyin.check_have_rebot_analyse()
    # douyin.fudai_choujiang("66B0220930007938", 26)
    # douyin.test()
