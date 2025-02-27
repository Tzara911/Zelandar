from setuptools import setup

APP = ['my_calendar.py']  # 你的 Python 脚本文件
DATA_FILES = []  # 如果有额外的资源文件，如图像、模型等，添加路径
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'tkinterdnd2', 'PIL', 'pytesseract', 'transformers'],  # 你用到的库
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
