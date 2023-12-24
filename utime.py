import os
import datetime


format_string = "%Y-%m-%d %H:%M:%S"


def set_file_time(file_path, date_string):
    """
    修改指定文件的修改时间为指定时间
    """
    specified_datetime = datetime.datetime.strptime(date_string, format_string)

    # 修改文件的访问时间和修改时间
    os.utime(file_path, (specified_datetime.timestamp(), specified_datetime.timestamp()))
    print(f"Modified {file_path} modification time.")


def set_folder_time(folder_path, date_string):
    """
    修改指定文件夹下直接文件的修改时间为指定时间
    """
    specified_datetime = datetime.datetime.strptime(date_string, format_string)

    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            # 修改文件的访问时间和修改时间
            os.utime(file_path, (specified_datetime.timestamp(), specified_datetime.timestamp()))
            print(f"Modified {file_path} modification time.")


if __name__ == '__main__':
    # 替换以下路径为你要遍历的文件夹路径
    # folder_path = "D:/csc/Pictures/2023-04-20"
    file_path = r"D:\csc\Pictures\All\2023-12-23\2023\12\20231222_192203_Fri_99934.jpg"

    # 用指定的格式将字符串转换为 datetime 对象
    date_string = "2023-09-09 19:48:00"

    set_file_time(file_path, date_string)
