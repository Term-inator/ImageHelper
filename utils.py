import nt
import os
import re
from collections import deque
from pathlib import Path
from datetime import datetime, timezone
from typing import cast, Self
from zoneinfo import ZoneInfo

import rawpy
import yaml
from PIL import Image
from pillow_heif import register_heif_opener
import exiftool # PyExifTool==0.4.13
from enum import Enum


register_heif_opener()
img_suffix = ('.jpg', '.JPG', '.png', '.PNG', '.heic', '.HEIC', '.heif', '.HEIF', '.jpeg', '.JPEG', '.webp', '.WEBP')
video_suffix = ('.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI', '.m4v', '.M4V', '.gif', '.GIF')
raw_img_suffix = ('.CR3', '.cr3', '.NEF', '.nef', '.ARW', '.arw', '.RAF', '.raf', '.RW2', '.rw2', '.ORF', '.orf', '.SRW', '.srw', '.PEF', '.pef', '.CR2', '.cr2', '.DNG', '.dng')


# 建议使用 load_media_batch
def load_images(folder):
    images: [nt.DirEntry] = []

    with os.scandir(folder) as it:
        for entry in it:
            if entry.is_dir():
                # 递归调用
                images.extend(load_images(entry.path))
            else:
                # 判断文件后缀
                if entry.name.lower().endswith(img_suffix):
                    images.append(entry)
    return images


# 建议使用 load_media_batch
def load_media(folder):
    files = []
    suffix = img_suffix + video_suffix + raw_img_suffix
    for filename in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, filename)):
            _files = load_media(os.path.join(folder, filename))
            files.extend(_files)

        if filename.endswith(suffix):
            files.append(os.path.join(folder, filename))
    return files


class MediaType(Enum):
    IMAGE = 'image'
    VIDEO = 'video'
    RAW_IMAGE = 'raw_image'
    UNKNOWN = 'unknown'

    @classmethod
    def from_filename(cls, filename: str):
        if filename.lower().endswith(img_suffix):
            return cls.IMAGE
        elif filename.lower().endswith(video_suffix):
            return cls.VIDEO
        elif filename.lower().endswith(raw_img_suffix):
            return cls.RAW_IMAGE
        else:
            return cls.UNKNOWN

    @classmethod
    def get_suffix_list(cls, media_type: list[Self]):
        """
        根据媒体类型列表返回对应的文件后缀列表
        """
        suffix_list = []
        for m_type in media_type:
            if m_type == cls.IMAGE:
                suffix_list.extend(img_suffix)
            elif m_type == cls.VIDEO:
                suffix_list.extend(video_suffix)
            elif m_type == cls.RAW_IMAGE:
                suffix_list.extend(raw_img_suffix)
        return tuple(suffix_list)


    @classmethod
    def all_media(cls):
        return [cls.IMAGE, cls.VIDEO, cls.RAW_IMAGE]

    @classmethod
    def all_image(cls):
        return [cls.IMAGE, cls.RAW_IMAGE]


def load_media_batch(folder: str, batch_size : int = 64, media_type : list[MediaType] = None, all_files: bool = False):
    """
    批量加载媒体文件，返回一个生成器，每次返回一个 batch 的媒体文件列表。
    :param folder: 文件夹路径
    :param batch_size: 每个 batch 的大小
    :param media_type: 媒体类型列表，默认为 None，表示加载所有类型的媒体文件
    :param all_files: 是否加载所有文件，False 时不加载已经处理过的文件（存放于 year/month 文件夹下）
    """
    # all_files: 是否加载所有文件，False 时不加载已经处理过的文件（存放于 year/month 文件夹下）
    if media_type is None:
        media_type = MediaType.all_media()
    suffix = MediaType.get_suffix_list(media_type)
    batch = []

    def yield_batches():
        """ 每次确保 `yield` 出来的 batch 维持在 `batch_size` """
        nonlocal batch
        while len(batch) >= batch_size:
            yield batch[:batch_size]  # `yield` 出 `batch_size` 个文件
            batch = batch[batch_size:]  # 保留剩余的部分

    with os.scandir(folder) as entries:
        for file_entry in entries:
            if file_entry.is_dir():
                if not all_files:
                    continue
                if re.match(r'\d{4}', file_entry.name):
                    year = re.match(r'\d{4}', file_entry.name).group()
                    subfolder = os.path.join(folder, year)
                    for sub_batch in load_media_batch(subfolder, batch_size, media_type, all_files):
                        batch.extend(sub_batch)
                elif re.match(r'\d{2}', file_entry.name):
                    month = re.match(r'\d{2}', file_entry.name).group()
                    subfolder = os.path.join(folder, month)
                    for sub_batch in load_media_batch(subfolder, batch_size, media_type, all_files):
                        batch.extend(sub_batch)
            elif file_entry.is_file() and file_entry.name.endswith(suffix):
                batch.append(file_entry)  # 直接存储 DirEntry 对象
            yield from yield_batches()

    # 处理最后一批不足 batch_size 的文件
    if batch:
        yield batch


# deprecated: similarity 比较不再加载所有图片
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


def del_image_dry_run(image_entry: nt.DirEntry):
    filename = Path(image_entry.name).stem
    folder = os.path.dirname(image_entry.path)
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.name.startswith(filename):
                print('delete', entry.name)


def del_image(image_entry: nt.DirEntry):
    filename = Path(image_entry.name).stem
    folder = os.path.dirname(image_entry.path)
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.name.startswith(filename):
                print('delete', entry.name)
                os.remove(entry.path)

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


class TimeRange:
    """
    表示一个时间范围，包含起始时间和结束时间
    """
    def __init__(self, from_time: datetime | None, to_time: datetime | None):
        self.from_time = from_time
        self.to_time = to_time

        # 如果 from_time 为 None，设置为最小的 UTC 时间
        if self.from_time is None:
            self.from_time = datetime.min.replace(tzinfo=timezone.utc)

        # 如果 to_time 为 None，设置为最大的 UTC 时间
        if self.to_time is None:
            self.to_time = datetime.max.replace(tzinfo=timezone.utc)

    def contains(self, dt: datetime) -> bool:
        """
        检查一个 datetime 是否在时间范围内
        """
        if dt < self.from_time:
            return False
        if dt > self.to_time:
            return False
        return True

    def __str__(self):
        return f"{self.from_time.isoformat()} - {self.to_time.isoformat()}"

    def __repr__(self):
        return self.__str__()


class ZoneRange:
    """
    表示一个时区范围，包含时区名称、时间范围列表和保存时转换为的时区
    含义为在这些时间范围内是该时区的时间，按该时区读取图片，并转换为指定的时区（如果有的话）
    """
    def __init__(self, name, ranges: list[dict], save_as=None):
        self.name = name # 时区名称
        self.ranges = [TimeRange(r.get('from'), r.get('to')) for r in ranges] if ranges else [] # 时间范围列表
        self.save_as = save_as # 保存时转换为的时区，如果没有则不转换

    def matches(self, dt: datetime) -> bool:
        """
        判断指定的 datetime 是否匹配该时区范围
        """
        if not self.ranges:
            return True

        # 如果 datetime 没有时区信息，则假设是当前时区
        _dt = dt
        if _dt.tzinfo is None:
            _dt = _dt.replace(tzinfo=ZoneInfo(self.name))

        # 遍历所有的时间范围，检查是否包含该 datetime
        for time_range in self.ranges:
            if time_range.contains(_dt):
                return True
        return False

    def __str__(self):
        ranges_str = ', '.join([str(r) for r in self.ranges])
        return f"{self.name}: [{ranges_str}]"

    def __repr__(self):
        return self.__str__()


class Folder:
    def __init__(self, name: str, parent_path: str, zones: deque[list[ZoneRange]]):
        self.name: str = name
        self.path: str = cast(str, os.path.join(parent_path, name))
        self.zones: deque[list[ZoneRange]] = zones
        self.sub_folders: list[Self] = []  # 存储子文件夹的列表

    def add_subfolder(self, subfolder_data: dict, zones: deque[list[ZoneRange]]=None) -> None:
        """递归创建子文件夹，并将父文件夹的时区信息传递给子文件夹"""
        subfolder = Folder.create_from_data(subfolder_data, self.path, zones)

        self.sub_folders.append(subfolder)

    @classmethod
    def create_from_data(cls, folder_data: dict, parent_path: str = '', parent_zones: deque[list[ZoneRange]] = None) -> Self:
        """根据提供的数据创建 Folder 对象，并结合父文件夹的时区信息"""
        if parent_zones is None:
            parent_zones = deque()

        zones = [ZoneRange(zone['name'], zone.get('ranges'), zone.get('save_as')) for zone in folder_data.get('tz', [])]
        combined_zones = parent_zones.copy()  # 使用 copy() 而不是 deepcopy()，因为 zones 是 ZoneRange 的实例，不需要深拷贝
        if len(zones) != 0:
            combined_zones.appendleft(zones)
        folder = cls(folder_data['name'], parent_path, combined_zones)

        # 处理子文件夹的递归
        for sub_folder_data in folder_data.get('folder', []):
            folder.add_subfolder(sub_folder_data, combined_zones)

        return folder

    def get_zone_range(self, dt: datetime) -> ZoneRange:
        """
        根据指定时间查找适用的时区范围
        """
        for zone in self.zones:
            for zone_range in zone:
                if zone_range.matches(dt):
                    return zone_range
        raise ValueError('no zone range')

    def convert_to_zone(self, dt: datetime) -> datetime:
        """
        根据指定的时间和时区，转换到正确的时区
        """
        zone_range = self.get_zone_range(dt)

        # 如果 datetime 没有时区信息，则假设是当前时区
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(zone_range.name))
        # 如果时区范围没有指定保存时转换为的时区，则使用当前时区
        else:
            dt = dt.astimezone(ZoneInfo(zone_range.name))

        # 如果指定了保存时转换为的时区，则转换为该时区
        if zone_range.save_as:
            dt = dt.astimezone(ZoneInfo(zone_range.save_as))

        return dt

    def get_relative_path(self, path: str) -> str:
        """
        获取相对于该文件夹的路径
        :param path: 绝对路径或相对路径
        :return: 相对于该文件夹的路径
        """
        if not path.startswith(self.path):
            raise ValueError(f"Path {path} is not under folder {self.path}")

        return os.path.relpath(path, self.path)

    def zones_str(self):
        return ', '.join([str(zones) for zones in self.zones])

    def __iter__(self):
        """递归遍历文件夹及其子文件夹"""
        yield self
        for subfolder in self.sub_folders:
            yield from subfolder


def load_config(config_file: str = 'folders.yaml') -> Folder:
    with open(config_file, 'r', encoding='utf-8') as f:
        folders = yaml.load(f, Loader=yaml.FullLoader)

    return Folder.create_from_data(folders.get('folder', [])[0])


def get_metadata(file: nt.DirEntry):
    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(file.path)
        return metadata


def get_image_time(file: nt.DirEntry) -> datetime:
    """
    获取图片文件的拍摄时间：
    - 优先 EXIF 中的 DateTimeOriginal + OffsetTimeOriginal
    - fallback: 使用文件系统修改时间（mtime），不要带时区，因为时间似乎是对的，只是时区是本地时区。后面判断出时区后替换掉时区即可
    """
    with exiftool.ExifTool() as et:
        date_time_original = et.get_tag("EXIF:DateTimeOriginal", file.path)
        offset_time_original = et.get_tag("EXIF:OffsetTimeOriginal", file.path)

        if date_time_original and offset_time_original:
            # 有时区偏移 → 拼接并用 %z 解析
            dt_str = f"{date_time_original} {offset_time_original}"
            dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S %z')

            return dt

        # fallback: 使用文件修改时间
        mtime = os.path.getmtime(file.path)
        return datetime.fromtimestamp(mtime)


def get_media_time(file: nt.DirEntry) -> datetime:
    """
    获取媒体文件的拍摄时间
    """
    if file.name.endswith(img_suffix):
        return get_image_time(file)
    else:
        # 对于其他类型的文件，直接使用 mtime
        mtime = os.path.getmtime(file.path)
        return datetime.fromtimestamp(mtime)


def get_mtime(file: nt.DirEntry) -> datetime:
    """
    获取图片的修改时间（UTC）：
    - 若有 EXIF 中的 DateTimeOriginal + OffsetTimeOriginal，则解析并转为 UTC。
    - 否则使用文件系统的 mtime
    """
    with exiftool.ExifTool() as et:
        date_time_original = et.get_tag("EXIF:DateTimeOriginal", file.path)
        offset_time_original = et.get_tag("EXIF:OffsetTimeOriginal", file.path)

    if date_time_original and offset_time_original:
        # 解析 EXIF 中的时间
        dt_str = f"{date_time_original} {offset_time_original}"
        dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S %z')
        return dt.astimezone(timezone.utc)
    else:
        # 使用文件系统的修改时间
        mtime = os.stat(file.path).st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc)


def is_live_photo(file: nt.DirEntry):
    with exiftool.ExifTool() as et:
        return et.get_tag("QuickTime:LivePhotoAuto", file.path) == 1


def get_content_uuid(file: nt.DirEntry):
    with exiftool.ExifTool() as et:
        uuid = et.get_tag("QuickTime:ContentIdentifier", file.path) or et.get_tag("MakerNotes:ContentIdentifier", file.path)
        # IOS 16 以下可能会是 MediaGroupUUID，不确定
        return uuid


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


def raw_to_jpg(file: nt.DirEntry, thumbnail: bool = False):
    """
    将原始图像文件转换为 JPG 文件。
    如果 thumbnail 为 True，则提取缩略图，否则使用 rawpy 读取并处理。
    """
    if file.name.endswith(raw_img_suffix):
        if thumbnail:
            # 提取缩略图
            with rawpy.imread(file.path) as raw:
                thumbnail = raw.extract_thumb()

            filename = file.path.replace(Path(file.name).suffix, '.jpg')

            if thumbnail.format == rawpy.ThumbFormat.JPEG:
                # 'thumbnail.data' is the full JPEG buffer
                with open(filename, 'wb') as f:
                    f.write(thumbnail.data)
        else:
            with rawpy.imread(file.path) as raw:
                # 后处理为 RGB 图像
                rgb = raw.postprocess()

            # 使用 Pillow 将 RGB 图像保存为 JPG
            filename = file.path.replace(Path(file.name).suffix, '.jpg')
            img = Image.fromarray(rgb)

            img = img.convert('RGB')  # 转换为 RGB 模式
            img.save(filename)

        # 提取原始文件的 EXIF 和 XMP 元数据，使用 exiftool
        with exiftool.ExifTool() as et:
            et.execute(
                "-overwrite_original".encode('utf-8'),
                f"-TagsFromFile={file.path}".encode('utf8'),
                os.path.join(os.path.dirname(file.path), filename).encode('utf8'),
            )

        # 设置修改时间为原文件的修改时间
        os.utime(filename, (file.stat().st_atime, file.stat().st_mtime))

        os.remove(file.path)



def has_unique_suffix(file_entry_list: list[nt.DirEntry]) -> bool:
    """
    检查文件列表中的文件名是否有唯一的后缀。
    如果存在两个相同的后缀，则返回 False
    """
    suffixes = set()
    for file_entry in file_entry_list:
        suffix = Path(file_entry.name).suffix.lower()
        if suffix in suffixes:
            return False
        suffixes.add(suffix)
    return True


def file_size_to_str(file_size: int) -> str:
    """
    将文件大小转换为字符串表示，保留四位小数，单位为 B、KB 或 MB
    """
    units = ['B', 'KB', 'MB']
    for unit in units:
        if file_size < 1024:
            return f'{file_size:.4f}{unit}'
        file_size /= 1024

    return f'{file_size:.4f}{units[-1]}'


def get_image_raw_size(image_entry: nt.DirEntry) -> int:
    """
    获取图片字节数（宽 * 高 * 通道数）
    """
    image = Image.open(image_entry.path)
    return image.size[0] * image.size[1] * len(image.getbands())


if __name__ == '__main__':
    folder = r"D:\csc\Pictures\All\旅行\Arizona\Page\Antelope Canyon\2024\04"
    for batch in load_media_batch(folder, 64):
        for file_entry in batch:
            raw_to_jpg(file_entry, thumbnail=True)