"""
douyin_guaji_maa.py
===================
抖音福袋挂机入口 —— MaaFramework 版

使用方式：
  python douyin_guaji_maa.py

主要改进（相对于 douyin_guaji_V3.3.py）：
  - 不再需要手动填写设备 device_id，自动扫描 ADB 设备
  - 启动即自动连接，分辨率通过截图自动读取
  - y_pianyi 偏移值保持不变，刘海屏/模拟器用户按需调整
"""

from douyin_fudai_maa import FudaiAnalyse


class FudaiGuaji:
    def __init__(self):
        self.analyser = FudaiAnalyse()

    def guaji(self, y_pianyi: int = 0):
        """
        启动挂机主循环。

        参数：
            y_pianyi: y 轴偏移值。
                      - 大多数手机填 0
                      - 刘海屏 / 挖孔屏若福袋检测不到，尝试填正数（向下偏移）
                      - 模拟器分辨率不标准时也可能需要调整

        选择设备：
            程序启动后会自动扫描 ADB 设备并让你选择。
            MuMu 模拟器需先在「模拟器 → 设置 → ADB 调试」中开启 ADB 连接。
        """
        ops = self.analyser.ops

        # 自动扫描并选择设备
        device = ops.select_device()
        if not device:
            print("未找到设备，10 秒后重试...")
            ops.delay(10)
            return self.guaji(y_pianyi)

        # 连接设备
        if not ops.connect(device):
            print("设备连接失败，10 秒后重试...")
            ops.delay(10)
            return self.guaji(y_pianyi)

        # 启动主循环
        self.analyser.fudai_choujiang(
            y_pianyi=y_pianyi,
            needswitch=True,
            wait_minutes=5,
        )


if __name__ == '__main__':
    choujiang = FudaiGuaji()
    # ↓ 只需改这里的数字：y 轴偏移量（像素，基于 2400 高度换算）
    # 大多数手机填 0，刘海屏如检测不到福袋尝试填 30~80
    choujiang.guaji(y_pianyi=0)
