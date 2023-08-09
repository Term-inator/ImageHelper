import imagehash
import matplotlib.pyplot as plt

import utils

folder = 'D:/csc/Pictures/2023-04-20'
image_files = utils.load_images(folder)
images = utils.read_images(image_files, mode='L')

print(len(image_files))

hashes = []
for image in images:
    hashes.append(imagehash.dhash(image))

similar_images = []
img_mark = set()  # 已经检查过相似度的图片
for i in range(len(images)):
    if i in img_mark:
        continue
    similar_to_i = [(image_files[i], 0)]
    img_mark.add(i)
    for j in range(i+1, len(images)):
        if hashes[i] - hashes[j] < 2:
            similar_to_i.append((image_files[j], hashes[i] - hashes[j]))
            img_mark.add(j)
    if len(similar_to_i) > 1:
        similar_images.append(similar_to_i)

for image_file_lst in similar_images:
    n = len(image_file_lst)
    # 展示全部图片，一行两张
    plt.figure(figsize=(20, 10))
    for index, (image_file, diff) in enumerate(image_file_lst):
        plt.subplot((n+1) // 2, 2, index+1)
        try:
            plt.imshow(plt.imread(image_file))
        except SyntaxError as e:
            print(f'Error: {e}')
            print(f'Error file: {image_file}')
            exit(1)
        plt.title(f'{image_file} {diff}\n{index}', fontsize=20)
    plt.show()
    rm_lst = input('remove list: ')
    if rm_lst == 'n':  # 不删除
        continue
    rm_lst = rm_lst.split()
    for rm in rm_lst:
        utils.del_image(image_file_lst[int(rm)][0])

