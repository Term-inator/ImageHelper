import nt
import os
import json

import imagehash
import matplotlib.pyplot as plt
from datasketch import MinHashLSH, MinHash
from PIL import Image

import utils


# 支持中文
plt.rcParams['font.sans-serif'] = ['SimHei']


# 加载缓存（如果存在）
def load_cache(cache_file='cache.json'):
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
            print(f'Cache loaded from {cache_file}')
            return cache
    return {}


# 保存缓存
def save_cache(cache_file='cache.json', cache=None):
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=4)
    print(f'Cache saved to {cache_file}')


# 计算 pHash
def compute_phash(image_entry):
    try:
        img = Image.open(image_entry.path).convert('L')  # 转灰度
    except OSError:
        print('cannot open', image_entry.path)
        raise
    hash = str(imagehash.phash(img))
    img.close()
    return hash


# pHash 转 MinHash（用于 LSH 近似搜索）
def hash_to_minhash(phash):
    # 将 pHash 转为 bit 串，例如 64 位二进制
    bit_hash = [int(b) for b in bin(int(str(phash), 16))[2:].zfill(64)]
    m = MinHash(num_perm=128)

    # 把每一位 bit 的位置当作“token”，插入 MinHash
    for i, bit in enumerate(bit_hash):
        if bit:
            m.update(str(i).encode('utf8'))
    return m


# 计算哈明距离
def hamming_distance(hash1, hash2):
    return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')


# LSH 初始化（阈值 0.8，允许一定误差）
lsh = MinHashLSH(threshold=0.8, num_perm=128)


def query_similar_images(folders: utils.Folder, phash_db: dict[str, str]):
    # 记录已处理的图片
    print('Querying similar images...')
    checked_images = set()
    similar_groups: list[tuple[nt.DirEntry, int]] = []
    image_entries: list[nt.DirEntry] = []

    for folder in folders:
        print(f'path: {folder.path}')
        batch_num = 0
        for batch in utils.load_media_batch(folder.path, 64, media_type=utils.MediaType.all_image(), all_files=True):
            for entry in batch:
                image_entries.append(entry)
                relative_path = folders.get_relative_path(entry.path)
                phash = phash_db[relative_path]
                mhash = hash_to_minhash(phash)
                lsh.insert(entry, mhash)

            batch_num += 1

    # 查找相似图片
    for entry in image_entries:
        if entry in checked_images:
            continue

        relative_path = folders.get_relative_path(entry.path)

        query_minhash = hash_to_minhash(phash_db[relative_path])
        candidates = lsh.query(query_minhash)  # LSH 近似匹配

        # 进一步用 pHash 计算哈明距离
        similar_images = [(entry, 0)]  # 自己也算一个
        checked_images.add(entry)

        for candidate in candidates:
            if candidate != entry and candidate not in checked_images:
                dist = hamming_distance(phash_db[relative_path], phash_db[folders.get_relative_path(candidate.path)])
                if dist <= 2:  # 设定 pHash 相似度阈值， 一般用 2
                    similar_images.append((candidate, dist))
                    checked_images.add(candidate)

        # 记录相似组
        if len(similar_images) > 1:
            similar_groups.append(similar_images)

    return similar_groups


def remove_similar_images(folder, similar_images):
    for image_entry_lst in similar_images:
        n = len(image_entry_lst)
        # 展示全部图片，一行两张
        fig = plt.figure(figsize=(20, 14))
        for index, (image_entry, diff) in enumerate(image_entry_lst):
            plt.subplot((n+1) // 2, 2, index+1)
            try:
                plt.imshow(plt.imread(image_entry.path))
            except SyntaxError as e:
                print(f'Error: {e}')
                print(f'Error file: {image_entry.path}')
                # exit(1)
                continue
            path_display = image_entry.path.replace(folder, '')
            # 过长换行
            if len(path_display) > 50:
                path_display = path_display[:50] + '\n' + path_display[50:]
            plt.title(f'{path_display} \n diff:{diff} index:{index}', fontsize=20)
        plt.show(block=False)
        # 获取 Tkinter 窗口并修改属性
        rm_lst = input('remove list: ')

        if rm_lst == 'n':  # 不删除
            continue
        rm_lst = rm_lst.split()
        for rm in rm_lst:
            utils.del_image_dry_run(image_entry_lst[int(rm)][0])
        confirm = input('confirm? (Y/n): ')
        plt.close()
        if confirm != 'n' and confirm != 'N':
            for rm in rm_lst:
                utils.del_image(image_entry_lst[int(rm)][0])


def export_similar_images(folder, similar_images):
    with open(f'{folder}\\similar_images.txt', 'w') as f:
        for image_entry_lst in similar_images:
            for image_entry, diff in image_entry_lst:
                f.write(f'{image_entry.path}\n')
            f.write('\n')


def generate_cache(folders: utils.Folder, save_interval=10):
    """
    :param folders: utils.Folder 对象，包含所有需要处理的文件夹
    :param save_interval: 几批次保存一次缓存
    """
    cache_file = f'{folders.path}\\cache.json'
    cache = load_cache(cache_file)  # 加载缓存

    phash_db: dict[str, str] = {}  # 存储文件路径和对应的 pHash

    batch_processed = 0  # 处理的批次数

    for folder in folders:
        print(f'path: {folder.path}')
        batch_num = 0
        for batch in utils.load_media_batch(folder.path, 64, media_type=utils.MediaType.all_image(), all_files=True):
            print(f'batch {batch_num}, size {len(batch)}')

            all_cached = True
            for entry in batch:
                relative_path = folders.get_relative_path(entry.path)
                print(relative_path)
                # 如果路径在缓存中，直接使用缓存的 pHash
                if relative_path in cache:
                    phash = cache[relative_path]
                # 如果缓存中没有，计算 pHash 并存入缓存
                else:
                    all_cached = False
                    phash = compute_phash(entry)
                    cache[relative_path] = phash

                phash_db[relative_path] = phash

            batch_num += 1
            if not all_cached:
                batch_processed += 1

            if batch_processed != 0 and batch_processed % save_interval == 0:
                print(f'Saving cache after {batch_processed} batches...')
                save_cache(cache_file, cache)

    save_cache(cache_file, cache)  # 保存缓存

    return phash_db


# run after rename.py !!!!!!!!
# 因为 rename 会给 live 图赋予相同的名字，便于 similarity 里一起删除
if __name__ == '__main__':
    folders = utils.load_config('folders.yaml')

    phash_db = generate_cache(folders, save_interval=10)

    similar_images = query_similar_images(folders, phash_db)
    # TODO 删除已经被删除的图片的 cache

    print(f'Found {len(similar_images)} similar groups')
    remove_similar_images(folders.path, similar_images)
    # export_similar_images(folder, similar_images)