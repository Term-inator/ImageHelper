import os
import time
from datetime import datetime
import random

from PIL import Image

import utils


def get_image_format(file_path):
    try:
        # 不需要显式打开图像，直接通过Image格式获取图像格式
        with Image.open(file_path) as img:
            return img.format
    except IOError as e:
        print("Error:", e)
        return None


print(Image.EXTENSION)
unsupported_format = ['HEIF']


def rename(folder, file):
    last_modified_time = time.ctime(os.stat(file).st_mtime)
    dt = datetime.strptime(last_modified_time, '%a %b %d %H:%M:%S %Y')
    # 格式为 YYYYMMDD_HHMMSS_DAY_RND.PNG
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    if not os.path.exists(os.path.join(folder, year, month)):
        os.makedirs(os.path.join(folder, year, month))
    rand = random.randint(10000, 100000)
    suffix = os.path.splitext(file)[1]
    img_format = get_image_format(file)
    new_name = f'{dt.strftime("%Y%m%d_%H%M%S")}_{dt.strftime("%a")}_{rand}{".jpg" if img_format in unsupported_format else suffix}'
    # 如果文件所在位置和文件名已经符合要求，就不操作
    if os.path.dirname(file) == os.path.join(folder, year, month) and os.path.basename(file)[0:19] == new_name[
                                                                                                      0:19] and img_format not in unsupported_format:
        return
    if img_format not in unsupported_format:
        os.rename(file, os.path.join(folder, year, month, new_name))
    else:
        with Image.open(file) as img:
            img.save(os.path.join(folder, year, month, new_name))  # 转换图片格式
        # 设置修改时间
        os.utime(os.path.join(folder, year, month, new_name), (os.stat(file).st_atime, os.stat(file).st_mtime))
        os.remove(file)


def check(folder):
    suffix = ['.jpg', '.JPG', '.png', '.PNG', '.heic', '.HEIC']
    for year in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, year)):
            for month in os.listdir(os.path.join(folder, year)):
                for file in os.listdir(os.path.join(folder, year, month)):
                    file_path = os.path.join(folder, year, month, file)
                    if os.path.isdir(file_path):
                        print(f'{file_path} is a folder')
                        return False
                    last_modified_time = time.ctime(os.stat(file_path).st_mtime)
                    dt = datetime.strptime(last_modified_time, '%a %b %d %H:%M:%S %Y')
                    for suf in suffix:
                        if file_path.endswith(suf):
                            break
                    else:
                        continue
                    img_format = get_image_format(file_path)
                    if img_format in unsupported_format:
                        print(f'{file_path} is not supported')
                        return False
                    if os.path.dirname(file_path) != os.path.join(folder, year, month) or \
                            os.path.basename(file)[0:19] != f'{dt.strftime("%Y%m%d_%H%M%S")}_{dt.strftime("%a")}':
                        print(f'{file_path} is not correct')
                        return False
    return True


if __name__ == '__main__':
    folders = utils.load_folders()
    for folder in folders:
        print(f'path: {folder}')
        files = utils.load_media(folder)
        print(len(files))
        for file in files:
            rename(folder, file)
        utils.del_empty_folder(folder)
        print(check(folder))
