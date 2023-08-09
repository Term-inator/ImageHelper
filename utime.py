"""
修改指定文件夹下直接文件的修改时间为指定时间
"""

import os
import datetime

# 替换以下路径为你要遍历的文件夹路径
folder_path = "D:/csc/Pictures/2023-04-20"

# 用指定的格式将字符串转换为 datetime 对象
date_string = "2019-10-14 18:58:00"
format_string = "%Y-%m-%d %H:%M:%S"

specified_datetime = datetime.datetime.strptime(date_string, format_string)

for file in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file)
    if os.path.isfile(file_path):
        os.utime(file_path, (specified_datetime.timestamp(), specified_datetime.timestamp()))
        print(f"Modified {file_path} modification time.")
