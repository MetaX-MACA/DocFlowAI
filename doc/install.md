# 文档结构化工具安装说明

- [文档结构化工具安装说明](#文档结构化工具安装说明)
  - [安装 MetaX C500驱动和SDK](#安装-metax-c500驱动和sdk)
  - [使用Conda创建Python虚拟运行环境](#使用conda创建python虚拟运行环境)
  - [下载MinerU源码并替换文件](#下载mineru源码并替换文件)
  - [下载Docker镜像和准备运行环境](#下载docker镜像和准备运行环境)
  - [模型权重下载](#模型权重下载)
  - [安装多模态解析工具](#安装多模态解析工具)


推荐运行环境
- OS: Ubuntu >= 20.04
- Python: >= 3.10
- GPU: MetaX C500
- Driver/SDK Version: 2.31.0.4 or higger
- RAM: >= 128GB
- Docker: >=26.1.3
- 支持OpenAI SDK的LLM API Key 


## 安装 MetaX C500驱动和SDK

1. 前往 [沐曦开发者中心](https://sw-developer.metax-tech.com/member.php?mod=register) 注册账号。

2. 下载 MetaX C500 [驱动](https://developer.metax-tech.com/softnova/download?package_kind=Driver&dimension=metax&chip_name=%E6%9B%A6%E4%BA%91C500%E7%B3%BB%E5%88%97&deliver_type=%E5%88%86%E5%B1%82%E5%8C%85) and [SDK](https://developer.metax-tech.com/softnova/download?package_kind=SDK&dimension=metax&chip_name=%E6%9B%A6%E4%BA%91C500%E7%B3%BB%E5%88%97&deliver_type=%E5%88%86%E5%B1%82%E5%8C%85), 版本: 2.31.0.4及以上。请下载本地安装版本包。

3. 按照下载页面上的指令进行安装

4. 配置 `.bashrc` 环境变量
    
    ```
    vi ~/.bashrc
    ```
    添加以下环境变量
    ```shell
    export MACA_PATH=/opt/maca
    export MACA_CLANG_PATH=${MACA_PATH}/mxgpu_llvm/bin
    export PATH=${MACA_PATH}/bin:${MACA_PATH}/tools/cu-bridge/bin:${MACA_PATH}/tools/cu-bridge/tools:${MACA_CLANG_PATH}:${PATH}
    export LD_LIBRARY_PATH=${MACA_PATH}/lib:${MACA_PATH}/mxgpu_llvm/lib:${MACA_PATH}/ompi/lib:${LD_LIBRARY_PATH}
    export MXLOG_LEVEL=err
    ```
    更新环境变量
    ```
    source ~/.bashrc
    ```
5. 将当前用户添加到`video`用户组

    ```shell
    sudo usermod -aG video $USER
    newgrp video
    ```

6. 重启服务器

7. 开机后你可以使用 `mx-smi` 命令查看GPU信息

## 使用Conda创建Python虚拟运行环境
``` shell
# 下载安装conda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash ./Miniconda3-latest-Linux-x86_64.sh

# 配置pipy源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 创建运行环境
conda create -n docflow_ai python=3.10
conda activate docflow_ai
```

## 下载MinerU源码并替换文件
克隆项目代码到本地后，执行以下操作：

1. 在项目目录中下载MinerU源码
```shell
# git clone MinerU开源代码
git clone -b release-1.3.12  https://github.com/opendatalab/MinerU.git
```

2. 执行以下命令，使用项目中文件替换MinerU中文件

```shell
python replace_files.py ./code ./MinerU

# 复制文件
cp ./MinerU/magic_pdf/model/__init__.py ./MinerU/dolphin/model/

# 复制文件
mkdir -p ./MinerU/dolphin/resources/model_config
cp ./MinerU/magic_pdf/resources/model_config/model_configs.yaml ./MinerU/dolphin/resources/model_config/
```

3. 创建model目录，用于存放权重

若权重已下载，将其放在model目录下即可
```shell
mkdir model
```
权重目录结构如下所示
```
- model/
  - Dolphin/
  - Qwen25_VL_3B/
  - layoutreader/
  - models/
    - Layout/
    - MFD/
    - MFR/
    - OCR/
```

## 下载Docker镜像和准备运行环境

下载镜像 metax_doc_flow_ai:v1，链接：待补充


1. 加载镜像
```
docker load -i metax_doc_flow_ai:v1 
```

2. 启动容器 
请注意修改以下命令中的代码目录、权重目录路径

```shell
docker run  -itd --name metax_doc_flow_ai  --device=/dev/dri --device=/dev/mxcd --device=/dev/infiniband --privileged=true --group-add video --security-opt seccomp=unconfined   -v /path_to_project_dir:/code  -v /path_to_model_dir:/model   metax_doc_flow_ai:v1
```

若项目路径为 `/home/metax/DocFlowAI` ，则容器启动命令为
```shell
docker run  -itd --name metax_doc_flow_ai  --device=/dev/dri --device=/dev/mxcd --device=/dev/infiniband --privileged=true --group-add video --security-opt seccomp=unconfined   -v /home/metax/DocFlowAI:/code  -v /home/metax/DocFlowAI/model:/model  metax_doc_flow_ai:v1
```


进入容器后，使用 `mx-smi` 验证metax显卡是否正常
```shell
docker exec -it metax_doc_flow_ai /bin/bash

root@ba35f990724d:/# mx-smi
mx-smi  version: 2.2.4

=================== MetaX System Management Interface Log ===================
Timestamp                                         : Tue Jun 17 08:51:52 2025

Attached GPUs                                     : 1
+---------------------------------------------------------------------------------+
| MX-SMI 2.2.4                        Kernel Mode Driver Version: 2.14.8          |
| MACA Version: 2.33.0.5              BIOS Version: 1.24.4.0                      |
|------------------------------------+---------------------+----------------------+
| GPU         NAME                   | Bus-id              | GPU-Util             |
| Temp        Pwr:Usage/Cap          | Memory-Usage        | GPU-State            |
|====================================+=====================+======================|
| 0           MetaX C500             | 0000:01:00.0        | 0%                   |
| 45C         48W / 350W             | 858/65536 MiB       | Available            |
+------------------------------------+---------------------+----------------------+

+---------------------------------------------------------------------------------+
| Process:                                                                        |
|  GPU                    PID         Process Name                 GPU Memory     |
|                                                                  Usage(MiB)     |
|=================================================================================|
|  no process found                                                               |
+---------------------------------------------------------------------------------+

End of Log
```

## 模型权重下载
若权重已下载，将其放在model目录下即可
```shell
cd /code

export HF_ENDPOINT=https://hf-mirror.com
python ./MinerU/scripts/download_models_hf_dolphin.py
```

## 安装多模态解析工具
```shell
# 配置pipy源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

cd /code/MinerU
pip install  -e .
```

验证安装是否正常
```shell
root@ba35f990724d:/code/MinerU# magic-pdf --help
Usage: magic-pdf [OPTIONS]

Options:
  -v, --version                   display the version and exit
  -p, --path PATH                 local filepath or directory. support PDF,
                                  PPT, PPTX, DOC, DOCX, PNG, JPG files
                                  [required]
  -o, --output-dir PATH           output local directory  [required]
  -d, --debug BOOLEAN             Enables detailed debugging information
                                  during the execution of the CLI commands.
  -s, --start INTEGER             The starting page for PDF parsing, beginning
                                  from 0.
  -e, --end INTEGER               The ending page for PDF parsing, beginning
                                  from 0.
  -t, --method_type [mineru|dolphin]
                                  document AI alogrithm type. mineru or
                                  dolphin
  -n, --num_parrlel_inference INTEGER
                                  The number of parrlel inferences of the
                                  model
  -fv, --figure_vlm BOOLEAN       Perform vlm inferencing on an image to get
                                  its description
  --help                          Show this message and exit.
```
