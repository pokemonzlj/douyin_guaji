# 功能展示
用于在抖音直播间自动挂机领取福袋，只要手机不关机就能一直领取福袋  
部分奖品：  
![image](https://github.com/user-attachments/assets/53873f4b-b5fa-47df-8340-52c08991af48)  
# 使用方法
1.手机连接电脑，开启开发者选项，usb调试打开，电脑上CMD命令提示行中输入adb devices命令能找到设备ID  
2.手机页面初始化，打开抖音->个人中心->关注->直播中->随意进一个直播间  
3.然后执行douyin_guaji.py文件即可  
4.要是完全不知道咋弄或者运行后识别福袋内容有误，你可以到B站给叼哥充电，会帮你私人部署
## 注意
5.缺少各种库文件的需要自己安装一下，免费文字识别库已经更新到PaddleOCR图像识别库  
6.根据自己设备的情况，修改douyin_guaji.py文件中y轴的偏移像素值，可正可负，默认设置的Y轴值为403，通常调整区间在【-30,30】  
默认手机分辨率是1080*2400的像素，即使是相同的分辨率，可能也会因为手机顶部的刘海不一样导致存在Y的偏移 
![image](https://github.com/pokemonzlj/douyin_guaji/assets/35096840/127d1cf5-0814-4edf-846e-b9936e1cb108)

通过电脑的画图软件就能看图标的像素位置  
![image](https://github.com/pokemonzlj/douyin_guaji/assets/35096840/bb6ed6fb-84e1-463a-83c7-080c644f212d)  
关于判定福袋存不存在小图标  
![image](https://github.com/user-attachments/assets/f494242b-bd57-4969-bd95-eb4c77d8c39e)

# 看到最后了，白嫖成功记得点个星
