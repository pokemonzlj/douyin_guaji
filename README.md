# 功能展示
用于在抖音直播间自动挂机抢福袋，只要手机不关机就能永久在线抢福袋  
部分奖品：  
![image](https://github.com/user-attachments/assets/09f35598-e239-49ed-9d6a-e5347df5f3db)  
# 使用方法
1.手机连接电脑，开启开发者选项，usb调试打开，打开CMD通过adb devices命令能找到设备  
2.手机页面打开抖音->个人中心->关注->直播中->随意一个直播间  
3.然后执行douyin_guaji.py文件即可  
## 注意
4.缺库文件自己安装一下，如果有比现在pytesseract更好的免费文字识别库，文字识别能更精准的，请联系我做更新替换  
5.根据自己设备的情况，修改douyin_guaji.py文件中y轴的偏移像素，可正可负，我默认设置的Y轴在403，通常区间在【-30,30】  
本人挂机的手机是1080*2400的像素，即使是相同的分辨率，可能也会因为手机顶部的刘海不一样导致存在Y的偏移 
![image](https://github.com/pokemonzlj/douyin_guaji/assets/35096840/127d1cf5-0814-4edf-846e-b9936e1cb108)

通过电脑的画图软件就能看图标的像素位置  
![image](https://github.com/pokemonzlj/douyin_guaji/assets/35096840/bb6ed6fb-84e1-463a-83c7-080c644f212d)  
关于判定福袋存不存在小图标  
![image](https://github.com/user-attachments/assets/f494242b-bd57-4969-bd95-eb4c77d8c39e)

# 看到最后了，白嫖成功记得点个星
