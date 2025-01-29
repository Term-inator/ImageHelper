import os
import time
from datetime import datetime
import random

from PIL import Image
from pathlib import Path
import exiftool

import utils


def get_media_format(file_path):
    return Path(file_path).suffix[1:]


def get_content_uuid(file):
    """获取 Live Photo 的 MediaGroupUUID"""
    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(file)
        uuid = metadata.get("QuickTime:ContentIdentifier") or metadata.get("MakerNotes:ContentIdentifier")
        # IOS 16 以下可能会是 MediaGroupUUID，不确定
        return uuid


# before rename, get the file map
def get_file_map(files):
    # files: file list under the same folder
    file_map = {
        '': []  # files without UUID
    }  # UUID: [file1, file2, ...]

    for file in files:
        content_uuid = get_content_uuid(file)
        if content_uuid:
            if content_uuid not in file_map:
                file_map[content_uuid] = []
            file_map[content_uuid].append(file)
        else:
            file_map[''].append(file)

    # check if files with the same UUID have the same last modified time
    for content_uuid, file_list in file_map.items():
        if content_uuid == '':
            continue
        last_modified_time = os.stat(file_list[0]).st_mtime
        for file in file_list:
            if os.stat(file).st_mtime != last_modified_time:
                print(f'Warning: {file} has different last modified time')

    return file_map


def generate_new_file_folder_and_name(folder, file):
    last_modified_time = time.ctime(os.stat(file).st_mtime)
    dt = datetime.strptime(last_modified_time, '%a %b %d %H:%M:%S %Y')

    # 格式为 YYYYMMDD_HHMMSS_DAY_RND.PNG
    year = dt.strftime("%Y")
    month = dt.strftime("%m")

    rand = random.randint(10000, 99999)

    new_folder = os.path.join(folder, year, month)
    new_name = f'{dt.strftime("%Y%m%d_%H%M%S")}_{dt.strftime("%a")}_{rand}'

    return new_folder, new_name


print(Image.EXTENSION)
unsupported_format = ['HEIF', 'HEIC']


def rename(folder, file_map):
    for content_uuid, file_list in file_map.items():
        if len(file_list) == 0:
            continue
        new_folder, new_name = generate_new_file_folder_and_name(folder, file_list[0])
        for file in file_list:
            if content_uuid == '':
                new_folder, new_name = generate_new_file_folder_and_name(folder, file)

            if not os.path.exists(new_folder):
                os.makedirs(new_folder)

            suffix = Path(file).suffix
            media_format = get_media_format(file)
            if media_format in unsupported_format:
                suffix = '.jpg'

            new_name_with_suffix = new_name + suffix

            # 如果文件所在位置和文件名已经符合要求，就不操作
            if (os.path.dirname(file) == new_folder and os.path.basename(file)[0:19] ==
                    new_name and media_format not in unsupported_format):
                continue

            if media_format not in unsupported_format:
                os.rename(file, os.path.join(new_folder, new_name_with_suffix))
            else:
                with Image.open(file) as img:
                    img.save(os.path.join(new_folder, new_name_with_suffix))  # 转换图片格式
                # 设置修改时间为原文件的修改时间
                os.utime(os.path.join(new_folder, new_name_with_suffix), (os.stat(file).st_atime, os.stat(file).st_mtime))
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
                    img_format = get_media_format(file_path)
                    if img_format in unsupported_format:
                        print(f'{file_path} is not supported')
                        return False
                    if os.path.dirname(file_path) != os.path.join(folder, year, month) or \
                            os.path.basename(file)[0:19] != f'{dt.strftime("%Y%m%d_%H%M%S")}_{dt.strftime("%a")}':
                        print(f'{file_path} is not correct')
                        return False
    return True


if __name__ == '__main__':
    folders = utils.load_folders('fd_test.yaml')
    for folder in folders:
        print(f'path: {folder}')
        files = utils.load_media(folder)
        print(len(files))
        name_map = get_file_map(files)
        rename(folder, name_map)
        utils.del_empty_folder(folder)
        print(check(folder))
