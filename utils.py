import nt
import os

import yaml
from PIL import Image
from pillow_heif import register_heif_opener
import exiftool
from pathlib import Path
from enum import Enum


register_heif_opener()
img_suffix = ('.jpg', '.JPG', '.png', '.PNG', '.heic', '.HEIC', '.heif', '.HEIF', '.jpeg', '.JPEG', '.webp', '.WEBP', 'DNG', 'dng')
video_suffix = ('.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI', '.m4v', '.M4V', '.gif', '.GIF')


def load_images(image_folder):
    image_files = []
    suffix = img_suffix
    for filename in os.listdir(image_folder):
        if os.path.isdir(os.path.join(image_folder, filename)):
            _image_files = load_images(os.path.join(image_folder, filename))
            image_files.extend(_image_files)

        for suf in suffix:
            if filename.endswith(suf):
                image_files.append(os.path.join(image_folder, filename))
    return image_files


def load_media(folder):
    files = []
    suffix = img_suffix + video_suffix
    for filename in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, filename)):
            _files = load_media(os.path.join(folder, filename))
            files.extend(_files)

        for suf in suffix:
            if filename.endswith(suf):
                files.append(os.path.join(folder, filename))
    return files


def load_media_batch(folder, batch_size=64):
    suffix = img_suffix + video_suffix
    batch = []

    with os.scandir(folder) as entries:
        for file_entry in entries:
            if file_entry.is_dir():
                yield from load_media_batch(file_entry.path, batch_size)  # 递归处理子目录
            elif file_entry.is_file() and file_entry.name.endswith(suffix):
                batch.append(file_entry)  # 直接存储 DirEntry 对象

                # 当 batch_size 达到上限时，yield 一次
                if len(batch) >= batch_size:
                    yield batch
                    batch = []  # 清空 batch

    # 处理最后一批不足 batch_size 的文件
    if batch:
        yield batch


def read_images(image_files, mode='RGB'):
    images = []
    for image_file in image_files:
        try:
            with Image.open(image_file) as img:
                images.append(img.convert(mode))
        except OSError as e:
            print(f'Error: {e}')
            print(f'Error file: {image_file}')
            exit(1)

    return images


def del_image(image_file: str):
    filename = Path(image_file).stem
    folder = os.path.dirname(image_file)
    for file in os.listdir(folder):
        if file.startswith(filename):
            print('delete', file)
            os.remove(os.path.join(folder, file))


def del_empty_folder(folder):
    if os.path.exists(folder):
        if len(os.listdir(folder)) == 0:
            print('delete', folder)
            os.rmdir(folder)
        else:
            for filename in os.listdir(folder):
                if os.path.isdir(os.path.join(folder, filename)):
                    del_empty_folder(os.path.join(folder, filename))
    else:
        print(f'{folder} not exists')


def load_folders(config_file='folders.yaml'):
    with open(config_file, 'r', encoding='utf-8') as f:
        folders = yaml.load(f, Loader=yaml.FullLoader)

    res = []

    def dfs(folder, parent_path=''):
        if 'folder' not in folder:
            if os.path.exists(parent_path) and os.path.isdir(parent_path):
                res.append(parent_path)
            else:
                print(f'{parent_path} not exists or not a folder')
            return
        for sub_folder in folder['folder']:
            dfs(sub_folder, os.path.join(parent_path, sub_folder['name']))

    dfs(folders)

    return res


def get_metadata(file: nt.DirEntry):
    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(file.path)
        return metadata


def is_live_photo(file: nt.DirEntry):
    with exiftool.ExifTool() as et:
        return et.get_tag("QuickTime:LivePhotoAuto", file.path) == 1


def get_content_uuid(file: nt.DirEntry):
    with exiftool.ExifTool() as et:
        uuid = et.get_tag("QuickTime:ContentIdentifier", file.path) or et.get_tag("MakerNotes:ContentIdentifier", file.path)
        # IOS 16 以下可能会是 MediaGroupUUID，不确定
        return uuid


class FileType(Enum):
    IMAGE = 0
    VIDEO = 1
    LIVE_PHOTO = 2


# before rename, get the file map
def get_file_entry_map(entries: [nt.DirEntry]):
    # entries: entry list under the same folder
    file_entry_map = {
        '': []  # files without UUID
    }  # UUID: [entry1, entry2, ...]

    for file_entry in entries:
        content_uuid = get_content_uuid(file_entry)
        if content_uuid:
            if content_uuid not in file_entry_map:
                file_entry_map[content_uuid] = []
            file_entry_map[content_uuid].append(file_entry)
        else:
            file_entry_map[''].append(file_entry)

    # check if files with the same UUID have the same last modified time
    for content_uuid, file_entry_list in file_entry_map.items():
        if content_uuid == '':
            continue
        last_modified_time = os.stat(file_entry_list[0]).st_mtime
        for file_entry in file_entry_list:
            if os.stat(file_entry).st_mtime != last_modified_time:
                print(f'Warning: {file_entry} has different last modified time')

    return file_entry_map
