from douyin_fudai import fudai_analyse

class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def guaji(self):
        device_id = self.analyser.select_device()
        y_pianyi = 0
        if device_id == "66B0220930007938":
            y_pianyi = 26
            self.analyser.fudai_choujiang(device_id, y_pianyi, False, 15)
        else:
            self.analyser.fudai_choujiang(device_id, y_pianyi, True, 15)

if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji()