# 2025 - Modified by MetaX Integrated Circuits (Shanghai) Co., Ltd. All Rights Reserved.
import json
import os
import shutil

import requests
from modelscope import snapshot_download
from huggingface_hub import snapshot_download as huggingface_hub_snapshot_download


def download_json(url):
    # 下载JSON文件
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    return response.json()


def download_and_modify_json(url, local_filename, modifications):
    if os.path.exists(url):
        data = json.load(open(url))
        config_version = data.get('config_version', '0.0.0')
        # if config_version < '1.2.0':
        #     data = download_json(url)
    else:
        data = json.load(open(local_filename))
        # data = download_json(url)

    # 修改内容
    for key, value in modifications.items():
        data[key] = value

    # 保存修改后的内容
    with open(local_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    mineru_patterns = [
        # "models/Layout/LayoutLMv3/*",
        "models/Layout/YOLO/*",
        "models/MFD/YOLO/*",
        "models/MFR/unimernet_hf_small_2503/*",
        "models/OCR/paddleocr_torch/*",
        # "models/TabRec/TableMaster/*",
        # "models/TabRec/StructEqTable/*",
    ]
    model_dir = snapshot_download('opendatalab/PDF-Extract-Kit-1.0', allow_patterns=mineru_patterns,
                                  local_dir="/model/", )

    #
    # ByteDance/Dolphin
    model_Dolphin_dir = snapshot_download('ByteDance/Dolphin', local_dir="/model/Dolphin", )

    # Qwen/Qwen2.5-VL-3B-Instruct
    model_Qwen25_VL_3B_dir = snapshot_download('Qwen/Qwen2.5-VL-3B-Instruct', local_dir="/model/Qwen25_VL_3B", )

    layoutreader_pattern = [
        "*.json",
        "*.safetensors",
    ]
    layoutreader_model_dir = huggingface_hub_snapshot_download('hantian/layoutreader',
                                                               allow_patterns=layoutreader_pattern,
                                                               local_dir="/model/layoutreader", )

    model_dir = model_dir + '/models'
    print(f'model_dir is: {model_dir}')
    print(f'layoutreader_model_dir is: {layoutreader_model_dir}')
    print(f'model_Qwen25_VL_3B_dir is: {model_Qwen25_VL_3B_dir}')
    print(f'model_Dolphin_dir is: {model_Dolphin_dir}')

    # paddleocr_model_dir = model_dir + '/OCR/paddleocr'
    # user_paddleocr_dir = os.path.expanduser('~/.paddleocr')
    # if os.path.exists(user_paddleocr_dir):
    #     shutil.rmtree(user_paddleocr_dir)
    # shutil.copytree(paddleocr_model_dir, user_paddleocr_dir)

    json_url = r'/code/MinerU/magic-pdf.template.json'
    config_file_name = 'magic-pdf.json'
    home_dir = os.path.expanduser('~')
    config_file = os.path.join(home_dir, config_file_name)

    json_mods = {
        'models-dir': model_dir,
        'models-dir_Dolphin': model_Dolphin_dir,
        'models-dir_Qwen25_VL_3B': model_Qwen25_VL_3B_dir,
        'layoutreader-model-dir': layoutreader_model_dir,
    }

    download_and_modify_json(json_url, config_file, json_mods)
    print(f'The configuration file has been configured successfully, the path is: {config_file}')
