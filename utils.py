import os
import yaml
from PIL import Image
from pillow_heif import register_heif_opener


register_heif_opener()
img_suffix = ['.jpg', '.JPG', '.png', '.PNG', '.heic', '.HEIC', '.heif', '.HEIF', '.jpeg', '.JPEG', '.webp', '.WEBP', 'DNG', 'dng']
video_suffix = ['.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI', '.m4v', '.M4V', '.gif', '.GIF']


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


def del_image(image_file):
    print('delete', image_file)
    if os.path.exists(image_file):
        os.remove(image_file)
    else:
        print(f'{image_file} not exists')


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
