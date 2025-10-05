# ImageHelper

运行 similarity.py 进行图片去重，出现相似图片时，输入 index 选择一张删除，输入 n 跳过

运行 rename.py 根据修改时间重命名图片

folders.yaml 为文件夹配置文件，格式如下：

```yaml
folder:
    tz: 
      - name: xxx # 按什么时区读取，如果没有 save_as，就按该时区保存
        range: # optional
          - from: xxx
            to: xxx
        save_as: xxx # optional 保存为什么时区
    name: xxx
    folder:
      name: xxx
      folder:
        - name: xxx
        - name: xxx
            - folder:
                - name: xxx
                - name: xxx
        - name: xxx
```

utime.py 为修改文件夹和文件修改时间的脚本


## bash 脚本
```bash
sudo apt install fd-find imagemagick
```


## TODO
用数据库存下没删除的相似文件
用mime判断文件类型