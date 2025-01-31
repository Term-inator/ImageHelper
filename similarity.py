import json
import nt
import os

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


# LSH 初始化（阈值 0.8，允许一定误差）
lsh = MinHashLSH(threshold=0.8, num_perm=128)
hash_db = {}  # 存储 pHash 值


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


def get_phash(image_entry, cache):
    cached = False
    if image_entry.name in cache:
        cached = True
        return cache[image_entry.name], cached
    phash = compute_phash(image_entry)
    cache[image_entry.name] = phash
    return phash, cached


# pHash 转 MinHash（用于 LSH 近似搜索）
def hash_to_minhash(phash):
    bit_hash = [int(b) for b in bin(int(str(phash), 16))[2:].zfill(64)]
    m = MinHash(num_perm=128)
    for i, bit in enumerate(bit_hash):
        if bit:
            m.update(str(i).encode('utf8'))
    return m


# 计算哈明距离
def hamming_distance(hash1, hash2):
    return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')


def query_similar_images(image_entries: [nt.DirEntry], cache, compare_old_images=False):
    # compare_old_images: False 旧图之间不比较
    # 计算 pHash 和 MinHash，并插入 LSH
    print('Computing pHash and MinHash...')
    old_images_set = set()
    for entry in image_entries:
        phash, cached = get_phash(entry, cache)
        if not compare_old_images and cached:
            old_images_set.add(entry)
            continue
        mhash = hash_to_minhash(phash)
        hash_db[entry] = phash
        lsh.insert(entry, mhash)

    # 记录已处理的图片
    print('Querying similar images...')
    checked_images = set()
    similar_groups: [(nt.DirEntry, int)] = []

    # 查找相似图片
    for entry in image_entries:
        if not compare_old_images and entry in old_images_set:
            continue
        if entry in checked_images:
            continue

        query_minhash = hash_to_minhash(hash_db[entry])
        candidates = lsh.query(query_minhash)  # LSH 近似匹配

        # 进一步用 pHash 计算哈明距离
        similar_images = [(entry, 0)]  # 自己也算一个
        checked_images.add(entry)

        for candidate in candidates:
            if candidate != entry and candidate not in checked_images:
                dist = hamming_distance(hash_db[entry], hash_db[candidate])
                if dist <= 2:  # 设定 pHash 相似度阈值
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


# run after rename.py !!!!!!!!
if __name__ == '__main__':
    folder = r"D:\csc\Pictures\All"
    cache_file = f'{folder}\\cache.json'
    cache = load_cache(cache_file)  # 加载缓存
    # folder = r"D:\csc\Pictures\test"
    image_entries = utils.load_images(folder)

    try:
        similar_images = query_similar_images(image_entries, cache, compare_old_images=True)
    except Exception:
        save_cache(cache_file, cache)  # 保存缓存
        raise

    cached_images = set(cache.keys())
    all_images = set([entry.name for entry in image_entries])
    # 删除已删除的图片
    for image in cached_images - all_images:
        del cache[image]

    save_cache(cache_file, cache)  # 保存缓存
    print(f'Found {len(similar_images)} similar groups')
    remove_similar_images(folder, similar_images)