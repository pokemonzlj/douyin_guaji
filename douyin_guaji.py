from douyin_fudai import fudai_analyse

class fudai_guaji:
    def __init__(self):
        self.analyser = fudai_analyse()

    def guaji(self):
        device_id = self.analyser.select_device()
        y_pianyi = 0
        if device_id == "XXXXXX":
            y_pianyi = 26
            self.analyser.fudai_choujiang(device_id, y_pianyi, False, 5)
        else:
            self.analyser.fudai_choujiang(device_id, y_pianyi, True, 5)

if __name__ == '__main__':
    choujiang = fudai_guaji()
    choujiang.guaji()