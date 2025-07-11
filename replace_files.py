# Copyright (c) 2025 MetaX Integrated Circuits (Shanghai) Co., Ltd. . All rights reserved.
import os
import shutil
import sys


def replace_files(src, dst):
    with open(r"diff.txt", encoding="utf-8") as f:
        ls = f.readlines()
    for l in ls:
        # print(l)
        ops = l.split('\t')
        op = ops[0].strip()
        file = ops[1].strip()
        os.makedirs(os.path.dirname(os.path.join(dst, file)),exist_ok=True)
        if op == 'A':
            print(f"复制{os.path.join(src, file)}到{os.path.join(dst, file)}")
            shutil.copy(os.path.join(src, file), os.path.join(dst, file))
        if op == 'M':
            print(f"覆盖{os.path.join(src, file)}到{os.path.join(dst, file)}")
            shutil.copy(os.path.join(src, file), os.path.join(dst, file))
    pass


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    replace_files(src, dst)
