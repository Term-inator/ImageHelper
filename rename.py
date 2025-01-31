import nt
import os
import re
from datetime import datetime, timezone
import random

from PIL import Image
from pathlib import Path

import utils


def get_media_format(file_entry: nt.DirEntry):
    return Path(file_entry.path).suffix[1:]


def generate_new_file_folder_and_name(folder, file_entry: nt.DirEntry):
    dt = datetime.fromtimestamp(file_entry.stat().st_mtime, tz=timezone.utc)

    # 格式为 YYYYMMDD_HHMMSS_DAY_RND.PNG
    year = dt.strftime("%Y")
    month = dt.strftime("%m")

    rand = random.randint(10000, 99999)

    new_folder = os.path.join(folder, year, month)
    new_name = f'{dt.strftime("%Y%m%d_%H%M%S")}_{dt.strftime("%a")}_{rand}'

    return new_folder, new_name


print(Image.EXTENSION)
unsupported_format = ['HEIF', 'HEIC']


def rename(folder, file_entry_map):
    for content_uuid, file_entry_list in list(file_entry_map.items()):
        # file_entry_list: [nt.DirEntry, nt.DirEntry, ...]
        if content_uuid != '':
            if len(file_entry_list) <= 1:
                continue
            new_folder, new_name = generate_new_file_folder_and_name(folder, file_entry_list[0])

        for file_entry in file_entry_list:
            if content_uuid == '':
                new_folder, new_name = generate_new_file_folder_and_name(folder, file_entry)

            if not os.path.exists(new_folder):
                os.makedirs(new_folder)

            suffix = Path(file_entry.path).suffix
            media_format = get_media_format(file_entry)
            if media_format in unsupported_format:
                suffix = '.jpg'

            new_name_with_suffix = new_name + suffix

            # 如果文件所在位置和文件名已经符合要求，就不操作
            # if (os.path.dirname(file_entry.path) == new_folder and file_entry.name[0:19] ==
            #         new_name[0:19] and media_format not in unsupported_format):
            #     continue

            if media_format not in unsupported_format:
                os.rename(file_entry.path, os.path.join(new_folder, new_name_with_suffix))
            else:
                with Image.open(file_entry.path) as img:
                    exif_data = img.info.get('exif')
                img.save(os.path.join(new_folder, new_name_with_suffix), exif=exif_data)  # 转换为jpg格式
                # 设置修改时间为原文件的修改时间
                os.utime(os.path.join(new_folder, new_name_with_suffix), (file_entry.stat().st_atime, file_entry.stat().st_mtime))
                os.remove(file_entry.path)

        del file_entry_map[content_uuid]


# 仅仅检查文件所在文件夹是否符合其last modified time，没有检查live图片的jpg和mov是否一一对应
def check(folder):
    print(f'Checking {folder}...')
    suffix = ('.jpg', '.JPG', '.png', '.PNG', '.heic', '.HEIC')

    with os.scandir(folder) as years:
        for year_entry in years:
            if not year_entry.is_dir() or not re.match(r'\d{4}', year_entry.name):  # 确保是年份文件夹
                continue

            with os.scandir(year_entry.path) as months:
                for month_entry in months:
                    if not month_entry.is_dir():  # 确保是月份文件夹
                        continue

                    with os.scandir(month_entry.path) as files:
                        for file_entry in files:
                            file_path = file_entry.path

                            if file_entry.is_dir():  # 发现子文件夹
                                print(f'{file_path} is a folder')
                                return False

                            # 获取修改时间
                            dt = datetime.fromtimestamp(file_entry.stat().st_mtime, tz=timezone.utc)

                            # 检查文件后缀
                            if not file_entry.name.endswith(suffix):
                                continue

                            # 获取文件格式
                            img_format = get_media_format(file_entry)
                            if img_format in unsupported_format:
                                print(f'{file_path} is not supported')
                                return False

                            # 检查文件路径和命名是否符合规范
                            expected_dir = os.path.join(folder, year_entry.name, month_entry.name)
                            expected_prefix = f'{dt.strftime("%Y%m%d_%H%M%S")}_{dt.strftime("%a")}'

                            if os.path.dirname(file_path) != expected_dir or not file_entry.name.startswith(expected_prefix):
                                print(f'{file_path} is not correct, expected {expected_dir}/{expected_prefix}')
                                return False

    return True  # 所有文件都符合要求


if __name__ == '__main__':
    folders = utils.load_folders('folders.yaml')
    for folder in folders:
        print(f'path: {folder}')
        file_entry_map = {
            '': []  # files without UUID
        }  # UUID: [file1, file2, ...]
        batch_num = 0
        for batch in utils.load_media_batch(folder, 64):
            print(f'batch {batch_num}, size {len(batch)}')
            file_entry_map_batch = utils.get_file_entry_map(batch)
            for uuid, files in file_entry_map_batch.items():
                if uuid not in file_entry_map:
                    file_entry_map[uuid] = []
                file_entry_map[uuid].extend(files)
            rename(folder, file_entry_map)
            utils.del_empty_folder(folder)
            batch_num += 1

        # 如果还有文件没有处理，说明有 UUID 的图片或者视频没有匹配到
        # 如果是视频，说明 live photo 的图片丢失，严重错误
        # 如果是图片，说明有图片没有匹配到视频，轻微错误，把这些图片放 file_entry_map[''] 里当作普通图片处理
        if len(file_entry_map.keys()) > 1:
            print(f'Error: {len(file_entry_map.keys())} UUIDs left')
            file_entry_map[''] = []
            for uuid, files in list(file_entry_map.items()):
                if uuid == '':
                    continue
                print(f'UUID: {uuid}, files: {len(files)}')
                if len(files) == 1:
                    if files[0].name.endswith(utils.video_suffix):
                        raise ValueError('Error: live photo image lost')
                    file_entry_map[''].extend(files)
                    del file_entry_map[uuid]
                else:
                    print(f'Error: {uuid} has {len(files)} files')
                    for file in files:
                        print(file.name)
                    raise ValueError('Error: UUID has multiple files')
            rename(folder, file_entry_map)

        print(check(folder))
