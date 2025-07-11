# 基于Dolphin的End2End文档解析

[Dolphin](https://github.com/bytedance/Dolphin) 是一个多模态文档解析模型，基于编码器-解码器Transformer架构，实现文档分析-解析范式

- 第一阶段—文档布局解析：按照自然阅读顺序生成文档元素序列，即每个文档元素的类别及其坐标。这里的文档元素值得是标题、图表、表格、脚注等。
- 第二阶段—元素内容解析：使用这些元素作为”锚点”，配合特定提示词实现并行内容识别，从而完成整页文档的内容提取。

![](https://pic1.zhimg.com/v2-d56b00b5cc3eae0a1211c8556ec421c8_1440w.jpg)
