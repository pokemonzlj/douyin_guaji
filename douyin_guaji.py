from douyin_fudai import fudai_analyse

class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def test(self):
        # self.get_screenshot()
        # self.cut_pic((405, 1300), (1000, 1480))  # 福袋内容详情
        # self.cut_pic((390, 1190), (690, 1280), False, 'fudai_countdown')  # 完整福袋详情倒计时
        # attend_button_text = self.analyse_pic_word('fudai_countdown', 2)
        # print(attend_button_text)
        # self.cut_pic((306, 2040 - self.y_pianyi), (780, 2110 - self.y_pianyi))  # 参与福袋抽奖的文字
        # self.cut_pic((306, 1290 - self.y_pianyi), (780, 1410 - self.y_pianyi))  # 立即领取奖品
        # self.analyser.cut_pic((357, 674 ), (740, 750 ))  # 没有抽中福袋位置
        # attend_button_text = self.analyser.analyse_pic_word('', 1)
        # print(attend_button_text)
        self.analyser.check_have_robot_analyse()

    def guaji(self):
        device_id = self.analyser.select_device()
        y_pianyi = 0
        if device_id == "66B0220930007938":
            y_pianyi =26
            self.analyser.fudai_choujiang(device_id, y_pianyi, False)
        else:
            self.analyser.fudai_choujiang(device_id, y_pianyi, True)


if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji()