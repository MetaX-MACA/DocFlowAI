# Nvidia卡上 Docker镜像创建指导说明

- [Nvidia卡上 Docker镜像创建指导说明](#nvidia卡上-docker镜像创建指导说明)
  - [创建基础镜像](#创建基础镜像)
  - [创建容器](#创建容器)
  - [设置conda源](#设置conda源)
  - [下载MinerU源码并替换文件](#下载mineru源码并替换文件)
  - [模型权重下载](#模型权重下载)
  - [安装magic-pdf](#安装magic-pdf)
  - [保存容器为新镜像](#保存容器为新镜像)

## 创建基础镜像
```shell
cd code/docker_nvidia
docker build -t nvidia_doc_flow_ai:v0 .
```

## 创建容器
若项目路径为 `/home/metax/DocFlowAI` ，则容器启动命令为
```shell
docker run -itd --name nvidia_doc_flow_ai_test --gpus=all -v /home/metax/DocFlowAI/model:/model -v /home/metax/DocFlowAI:/code  nvidia_doc_flow_ai:v0 /bin/bash
docker exec -it nvidia_doc_flow_ai /bin/bash
```

## 设置conda源
```sehll
vi ~/.condarc

# 粘贴复制以下内容
channels:
  - defaults
show_channel_urls: true
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud


# 保存退出后，更新conda 索引
conda clean -i
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

## 模型权重下载
若权重已下载，将其放在model目录下即可
```shell
cd /code

python ./MinerU/scripts/download_models_hf_dolphin.py
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

## 安装magic-pdf
```shell
cd /code/MinerU

cp magic-pdf.template.json /root/magic-pdf.json

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

## 保存容器为新镜像
```shell
docker commit nvidia_doc_flow_ai_test nvidia_doc_flow_ai:v1
```