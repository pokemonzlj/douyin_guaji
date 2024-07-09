import time

from douyin_fudai import fudai_analyse


class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def guaji(self, y_pianyi=0):
        """根据自己设备的分辨率，修改高度的偏移值"""
        device_id = self.analyser.select_device()
        if device_id:
            self.analyser.fudai_choujiang(device_id, y_pianyi, False, 5)
            return True
        time.sleep(10)
        self.guaji(y_pianyi)


if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji(0)  # 存在偏移的在这里填值既可
