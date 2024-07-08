1.手机连接电脑，开启开发者选项，usb调试打开，打开CMD通过adb devices命令能找到设备  
2.手机页面打开抖音->个人中心->关注->直播中->随意一个直播间  
3.然后执行douyin_guaji.py文件即可  
# 注意
4.缺库文件自己安装一下，如果有比现在pytesseract更好的免费文字识别库，文字识别能更精准的，请联系我做更新替换  
5.根据自己设备的情况，修改douyin_guaji.py文件中y轴的偏移像素，可正可负，我默认设置的Y轴在403，通常区间在【-30,30】  
本人挂机的手机是1080*2400的像素，即使是相同的分辨率，可能也会因为手机顶部的摄像头布局不一样影响图标的展示  
![image](https://github.com/pokemonzlj/douyin_guaji/assets/35096840/127d1cf5-0814-4edf-846e-b9936e1cb108)
通过电脑的画图软件就能看图标的像素位置  
![image](https://github.com/pokemonzlj/douyin_guaji/assets/35096840/bb6ed6fb-84e1-463a-83c7-080c644f212d)


