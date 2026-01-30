from douyin_fudai import fudai_analyse

class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def guaji(self):
        """挂机函数"""
        device_id = self.analyser.operation.select_device()
        if device_id:
            self.analyser.fudai_choujiang(device_id, False, 15)
            return True
        self.analyser.operation.delay(10)
        self.guaji()

if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji()
