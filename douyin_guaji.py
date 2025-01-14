import time
from douyin_fudai import fudai_analyse

class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def guaji(self, y_pianyi=0, x_resolution=1080, y_resolution=2400):
        """根据自己截图的实际情况，修改y轴即高度的偏移值"""
        device_id = self.analyser.select_device()
        if device_id:
            self.analyser.fudai_choujiang(device_id, y_pianyi, x_resolution, y_resolution, True, 5)
            return True
        time.sleep(10)
        self.guaji(y_pianyi)

if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji(0, 1080, 2400)  # 运行只改这里，参数第1个是y的偏移值，第2个是你手机横轴x的分辨率，第3个是你手机纵轴y的分辨率
