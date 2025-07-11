# 基于MinerU的Pipeline文档解析

[MinerU](https://github.com/opendatalab/MinerU) 是一个高质量的PDF解析工具，使用多个CNN模型实现版面分析、阅读顺序排序、OCR文字识别、表格解析、公式识别等。

PDF文档中包含大量知识信息，然而提取高质量的PDF内容并非易事。为此，MinerU将PDF内容提取工作进行拆解：

- 布局检测layout detection：使用`LayoutLMv3`模型进行区域检测，如图像，表格,标题,文本等；
- 公式检测：使用`YOLOv8`进行公式检测，包含行内公式和行间公式；
- 公式识别：使用`UniMERNet`进行公式识别；
- 表格识别TSR：使用`StructEqTable`进行表格识别；
- 光学字符识别OCR：使用`PaddleOCR`进行文本识别；

![img](https://pic1.zhimg.com/v2-0b4a6d57c3fba00e39f390328ab30444_1440w.jpg)
