# 文档结构化工具使用说明

- [文档结构化工具使用说明](#文档结构化工具使用说明)
  - [magic-pdf命令参数介绍](#magic-pdf命令参数介绍)
  - [magic-pdf命令输出结果介绍](#magic-pdf命令输出结果介绍)


## magic-pdf命令参数介绍

```shell
magic-pdf --help
Usage: magic-pdf [OPTIONS]

Options:
  -v, --version                   显示版本并退出
  -p, --path PATH                 [必需]本地文件路径或目录。支持 PDF、PPT、PPTX、DOC、DOCX、PNG、JPG 文件
  -o, --output-dir PATH           [必需]输出本地目录 
  -d, --debug BOOLEAN             在执行 CLI 命令期间启用详细的调试信息。
  -s, --start INTEGER             PDF解析的起始页，开始 从 0 开始。
  -e, --end INTEGER               PDF解析的结束页面，开始从 0 开始。
  -t, --method_type [mineru|dolphin] 文档智能AI算法类型. mineru or dolphin 默认为mineru的解析方式，如果需要多模态方式，改成
                                  dolphin
  -n, --num_parrlel_inference INTEGER 并行推理的数量 默认为200，并发数 
  -fv, --figure_vlm BOOLEAN       插图是否通过VLM获得插图的描述 默认为False，
  --help                          显示此消息并退出。


## show version
magic-pdf -v

## command line example

magic-pdf -p {some_pdf} -o {some_output_dir} -t dolphin  -fv True
```

## magic-pdf命令输出结果介绍

`{some_pdf}` 可以是单个 PDF 文件，也可以是包含多个 PDF 的目录。结果将保存在 `{some_output_dir}` 目录中。输出文件列表如下：

```shell
├── some_pdf.md                          # Markdown 文件
├── images                               # 图片存放目录
├── some_pdf_layout.pdf                  # 布局图
├── some_pdf_middle.json                 # 工具中间处理结果
├── some_pdf_model.json                  # 模型推理结果
├── some_pdf_origin.pdf                  # 原始PDF文件，或者其他类型文件首先转成的pdf文件
├── some_pdf_spans.pdf                   # 最小粒度 Bbox 位置信息图
└── some_pdf_content_list.json           # 按阅读顺序排列的富文本JSON
```

在Docker容器内运行四个脚本命令，验证工具是否运行正常
```shell
cd /code
mkdir result

# 使用MinerU原始pipeline方式进行OCR识别
magic-pdf -p /code/MinerU/demo/pdfs -o /code/result/pdfs_mineru  -t mineru

# 增减-fv 参数，对文档中图片调用VLM模型进行图像理解，额外补充对图片的描述文字
magic-pdf -p /code/MinerU/demo/pdfs -o /code/result/pdfs_mineru_fv  -t mineru  -fv True

# 使用dolphin模型进行OCR识别
magic-pdf -p /code/MinerU/demo/pdfs -o /code/result/pdfs_dolphin  -t dolphin

# 增减-fv 参数，对文档中图片调用VLM模型进行图像理解，额外补充对图片的描述文字
magic-pdf -p /code/MinerU/demo/pdfs -o /code/result/pdfs_dolphin_fv  -t dolphin  -fv True 
```

`/code/result`下运行生成结果如下
```shell
├── pdfs
├── pdfs_dolphin
│   ├── demo1
│   │   └── auto
│   │       ├── demo1_content_list.json
│   │       ├── demo1_layout.pdf
│   │       ├── demo1.md
│   │       ├── demo1_middle.json
│   │       ├── demo1_model.json
│   │       ├── demo1_origin.pdf
│   │       ├── demo1_spans.pdf
│   │       └── images
│   │           ├── 010b248e41dc78d1a43150717a7e8d551381e918431886568eed11d004fcc1e4.jpg
│   │           ├── 063c4109f3700431028eff3039c11d493e794fafff3549b608d93e3c35dfa568.jpg
│   │           ├── 1411bb3aa6b2b66e538ed2185ca80cb2f6a6149844c8517778b8da23e823661e.jpg
│   │           ├── 66051daa0c6ce5a16b2730d456855eec28d8ced2bbed2f8f6d4e984ae1fba258.jpg
│   │           ├── 939d3e586705e6351946f21004805e5fea572109822671ccb2d151dea45186be.jpg
│   │           ├── b3581502b09c44b70b61f9c8f5cbc5df4c37e3c73074bdb499a6334aeeb73a41.jpg
│   │           ├── b3b71a5337f40234ceae024bcffc3518cb34aa22e773b0582f2e1aeb83bb2fce.jpg
│   │           ├── d8555a9dd81bea76fad7032d32b2e84ae63d5797ed35fcea66667f5d6c562713.jpg
│   │           ├── dabf2948cf054bcb226da6c42082f511f6d00330e3ef0b65ab834e593a57e6c2.jpg
│   │           └── e5959a8283680bea3fc4f093978a5cdb120cad232deeeef788dc8c603780ada4.jpg
│   ├── demo2
...
```