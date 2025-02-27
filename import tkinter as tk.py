import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD

# 创建主窗口
root = TkinterDnD.Tk()
root.title("拖拽测试窗口")
root.geometry("400x200")

# 创建一个文本框，显示拖拽的文件路径
entry = tk.Entry(root, width=50)
entry.pack(pady=20)

# 处理拖拽文件的回调函数
def drop(event):
    entry.delete(0, tk.END)
    entry.insert(tk.END, event.data)  # 显示拖拽的文件路径

# 绑定拖拽事件
entry.drop_target_register(DND_FILES)
entry.dnd_bind('<<Drop>>', drop)

# 运行 Tkinter 事件循环
root.mainloop()
