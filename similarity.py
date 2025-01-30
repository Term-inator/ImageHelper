import json
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
def compute_phash(image_path):
    img = Image.open(image_path).convert('L')  # 转灰度
    return str(imagehash.phash(img))


def get_phash(image_path, cache):
    if image_path in cache:
        return cache[image_path]
    phash = compute_phash(image_path)
    cache[image_path] = phash
    return phash


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


def query_similar_images(folder, cache):
    image_files: [str] = utils.load_images(folder)

    # 计算 pHash 和 MinHash，并插入 LSH
    print('Computing pHash and MinHash...')
    for path in image_files:
        phash = get_phash(path, cache)
        mhash = hash_to_minhash(phash)
        hash_db[path] = phash
        lsh.insert(path, mhash)

    # 记录已处理的图片
    print('Querying similar images...')
    checked_images = set()
    similar_groups = []

    # 查找相似图片
    for path in image_files:
        if path in checked_images:
            continue

        query_minhash = hash_to_minhash(hash_db[path])
        candidates = lsh.query(query_minhash)  # LSH 近似匹配

        print(len(candidates))

        # 进一步用 pHash 计算哈明距离
        similar_images = [(path, 0)]  # 自己也算一个
        checked_images.add(path)

        for candidate in candidates:
            if candidate != path and candidate not in checked_images:
                dist = hamming_distance(hash_db[path], hash_db[candidate])
                if dist <= 1:  # 设定 pHash 相似度阈值
                    similar_images.append((candidate, dist))
                    checked_images.add(candidate)

        # 记录相似组
        if len(similar_images) > 1:
            similar_groups.append(similar_images)

    return similar_groups


def remove_similar_images(folder, similar_images):
    for image_file_lst in similar_images:
        n = len(image_file_lst)
        # 展示全部图片，一行两张
        plt.figure(figsize=(20, 14))
        for index, (image_file, diff) in enumerate(image_file_lst):
            plt.subplot((n+1) // 2, 2, index+1)
            try:
                plt.imshow(plt.imread(image_file))
            except SyntaxError as e:
                print(f'Error: {e}')
                print(f'Error file: {image_file}')
                # exit(1)
                continue
            path_display = image_file.replace(folder, '')
            # 过长换行
            if len(path_display) > 50:
                path_display = path_display[:50] + '\n' + path_display[50:]
            plt.title(f'{path_display} \n diff:{diff} index:{index}', fontsize=20)
        plt.show()
        rm_lst = input('remove list: ')
        if rm_lst == 'n':  # 不删除
            continue
        rm_lst = rm_lst.split()
        for rm in rm_lst:
            utils.del_image(image_file_lst[int(rm)][0])


# run after rename.py !!!!!!!!
if __name__ == '__main__':
    folder = r"D:\csc\Pictures\All"
    cache_file = f'{folder}\\cache.json'
    cache = load_cache(cache_file)  # 加载缓存
    # folder = r"D:\csc\Pictures\test"
    similar_images = query_similar_images(folder, cache)
    save_cache(cache_file, cache)  # 保存缓存
    # print(similar_images)
    remove_similar_images(folder, similar_images)