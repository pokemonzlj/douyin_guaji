"""Electron 启动的 Python worker 入口。"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Douyin 福袋挂机 worker")
    parser.add_argument("--device", help="ADB device serial")
    args = parser.parse_args()

    # Electron 将可写的配置、截图和日志目录作为当前工作目录传入。
    os.makedirs("pic", exist_ok=True)
    os.environ.setdefault("DYFD_DATA_DIR", os.getcwd())

    from douyin_fudai import fudai_analyse

    analyser = fudai_analyse()
    device_id = args.device or analyser.operation.select_device()
    if not device_id:
        print("未找到可用的 ADB 设备。请连接手机并开启 USB 调试。", flush=True)
        return 2

    print(f"已选择设备: {device_id}", flush=True)
    try:
        analyser.fudai_choujiang(device_id, False, 15)
    except KeyboardInterrupt:
        print("收到停止信号，挂机已退出。", flush=True)
        return 0
    except Exception as exc:
        print(f"挂机异常: {type(exc).__name__}: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
