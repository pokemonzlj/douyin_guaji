from douyin_fudai_V3.3 import fudai_analyse

class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def guaji(self, y_pianyi=0):
        """y_pianyi 对应y轴高度的偏移值"""
        device_id = self.analyser.operation.select_device()
        if device_id:
            self.analyser.fudai_choujiang(device_id, y_pianyi, True, 5)
            return True
        self.analyser.operation.delay(10)
        self.guaji(y_pianyi)

if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji(0)  # 运行只需改这里的0，对应是你手机纵轴y的偏移值

