"""覆盖 _pyinstaller_hooks_contrib 自带的 hook-lxml。

自带版本会调用 collect_submodules('lxml')，在本机 anaconda 环境下其隔离子进程
会崩溃（0xC0000005），导致打包中断。这里改为直接列出需要的子模块。
"""

hiddenimports = ['lxml.etree', 'lxml._elementpath', 'lxml.sax', 'lxml.html']
