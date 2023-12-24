# ImageHelper

运行 dhash.py 进行图片去重，出现相似图片时，输入 index 选择一张删除，输入 n 跳过

运行 rename.py 进行图片重命名

folders.yaml 为文件夹配置文件，格式如下：

```yaml
folder:
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