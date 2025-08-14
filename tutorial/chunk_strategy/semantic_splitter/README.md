## 语义切分教程（semantic_splitter）

本目录是一个“从分句到语义切分”的完整教程与示例集合，面向中文/英文及中英混排长文本的高质量切分场景（RAG 前处理、召回块构建等）。它提供：

- 基于 spaCy 的鲁棒分句工具，适配中/英文与段落换行
- 基于嵌入余弦相似度的“三阶段”语义切分算法：初始分块 → 句子附加 → 块合并
- 改进版切分器（V2/V3）：显式控制块大小，避免过度切分，保持句子完整性
- 可插拔的嵌入后端（云端 BGE-M3 或本地 SentenceTransformer），并内置磁盘级缓存（diskcache）
- 演示脚本与统计分析，便于理解与对比不同阈值/参数


### 目录结构

```
tutorial/semantic_splitter/
  ├─ cached_embedding_models.py        # 带磁盘缓存的嵌入包装
  ├─ embedding_models.py               # 嵌入后端（云端 BGE-M3、本地 SentenceTransformer）
  ├─ improved_semantic_splitter.py     # 改进版切分器（控制块大小，中文优先）
  ├─ improved_semantic_splitter_v2.py  # 改进版 V2（更严格的句子边界与尺寸控制）
  ├─ improved_semantic_splitter_v2_english.py  # 英文文本 V2 版本
  ├─ improved_semantic_splitter_v3.py  # 改进版 V3（基于 spaCy 分句）
  ├─ spacy_sentence_splitter_demo.py   # 分句演示脚本
  ├─ test_semantic_splitter.py         # 三阶段语义切分主实现与分句工具
  ├─ test_hongloumeng_split.py         # 《红楼梦》分句+语义切分演示
  ├─ process_hongloumeng.py            # 《红楼梦》全流程切分并落盘
  ├─ tests/test_cache.py               # 嵌入缓存策略验证
  └─ 红楼梦.txt                          # 示例中文长文本
```


### 教程要点与特性

- 分句层：
  - 使用 `spaCy` 的 `xx_sent_ud_sm` 多语言模型进行分句
  - 结合换行/段落分隔后处理，过滤极短片段，保持句子自然完整

- 语义层（基础切分器 `SemanticSplitter`）：
  - 初始分块（initial_threshold）：相邻句子的嵌入相似度低于阈值，则切块
  - 句子附加（appending_threshold）：若新块首句与前块末句相似度高，则附加
  - 块合并（merging_threshold）：若相邻两块平均嵌入相似度高，则合并
  - 支持 `max_chunk_size`（字符数）硬限制，避免单块超级长

- 改进层（`improved_*`）：
  - 显式控制块目标大小/最小/最大边界，优先在标点处分割
  - V3 使用 `spaCy` 分句作为第一步，适应中/英文混合文本

- 嵌入与缓存：
  - 可选择云端 BGE-M3（需要 `GUIJI_API_KEY` 与 `GUIJI_BASE_URL`）或本地 `SentenceTransformer`
  - `diskcache` 基于“句子+模型”哈希作为键，单句粒度缓存，命中后直接返回，显著加速


### 依赖与环境准备

建议使用 uv 管理虚拟环境。

```bash
# 1) 创建并激活虚拟环境（示例）
uv venv
source .venv/bin/activate

# 2) 安装依赖（若你项目根没有列出本教程依赖，请按需安装）
uv pip install spacy sentence-transformers diskcache python-dotenv openai numpy

# 3) 安装 spaCy 多语言分句模型
python -m spacy download xx_sent_ud_sm
```

如使用云端 BGE-M3（硅基流动兼容 OpenAI Embeddings API），需在环境中设置：

```bash
export GUIJI_API_KEY="your_api_key"
export GUIJI_BASE_URL="https://your-guiji-endpoint/v1"
```

或在目录下放置 `.env`：

```
GUIJI_API_KEY=your_api_key
GUIJI_BASE_URL=https://your-guiji-endpoint/v1
```


### 快速开始

1) 分句演示（验证 spaCy 模型是否可用）

```bash
cd tutorial/semantic_splitter
python spacy_sentence_splitter_demo.py
```

2) 直接对《红楼梦》进行分句+语义切分并落盘

```bash
cd tutorial/semantic_splitter
python process_hongloumeng.py
```

3) 运行更详细的演示（含阈值对比）

```bash
cd tutorial/semantic_splitter
python test_hongloumeng_split.py
```

4) 验证嵌入缓存策略

```bash
cd tutorial/semantic_splitter
python -m tests.test_cache | cat
```


### 代码用法示例

以基础三阶段切分器为例（中/英文都可，建议先用本目录的分句器）：

```python
# 在 tutorial/semantic_splitter 目录下运行
from test_semantic_splitter import SemanticSplitter, custom_sentence_splitter, read_text_file

text = read_text_file("红楼梦.txt")
sentences = custom_sentence_splitter(text)

splitter = SemanticSplitter(
    initial_threshold=0.4,
    appending_threshold=0.5,
    merging_threshold=0.5,
    max_chunk_size=850,
)

chunks = splitter.process_sentences(sentences)
print(f"Got {len(chunks)} chunks, example length: {len(chunks[0])}")
```

自定义嵌入后端（例如强制本地模型 + 缓存）：

```python
from embedding_models import LocalEmbeddingModel
from cached_embedding_models import CachedEmbeddingModel
from test_semantic_splitter import SemanticSplitter

embed = CachedEmbeddingModel(
    base_model=LocalEmbeddingModel(model_name="/path/to/bge-m3"),
    cache_dir="./embedding_cache",
    enable_cache=True,
)

splitter = SemanticSplitter(embed_model=embed, max_chunk_size=850)
chunks = splitter.process_sentences(["示例句子一。", "示例句子二。", "示例句子三。"])
```


### 算法说明（简要）

- 余弦相似度计算：`sentence-transformers` 的 `util.cos_sim` 实现
- 初始分块：相邻句子相似度 < initial_threshold → 开新块
- 句子附加：新块首句 与 前块末句 相似度 > appending_threshold → 附加到前块
- 块合并：相邻块平均嵌入相似度 > merging_threshold → 合并
- 改进器（V2/V3）：
  - 先按句子构建“尽量接近 target_chunk_size 的块”，再按相似度微调合并
  - 对于过长句子，优先在标点处分割，退化时按字符窗口强制切分


### 缓存机制

- `cached_embedding_models.CachedEmbeddingModel` 使用 `diskcache` 将“单句嵌入”以 `md5(模型名+句子)` 为键写入磁盘
- 批量编码时优先命中缓存，仅对未命中句子调用真实嵌入后端，返回时按原顺序重建
- 提供 `clear_cache()`、`get_cache_info()` 与 `warmup_cache()` 等辅助方法


### 常见问题（FAQ）

- 运行时报错找不到 `get_default_embedding_model` 或 `EmbeddingModelFactory`：
  - 说明：部分改进版切分器使用了 `get_default_embedding_model` 接口；如果你的 `embedding_models.py` 中暂未实现该函数/工厂，请：
    1) 直接改为手动构造后端并传入切分器（见“自定义嵌入后端”示例）；或
    2) 在 `embedding_models.py` 中补充：
       - `def get_default_embedding_model():` 返回一个默认后端（如 `BGE_M3_EmbeddingModel` 或 `LocalEmbeddingModel`）
       - `class EmbeddingModelFactory:` 提供 `create_model(model_type, **kwargs)` 工厂方法

- spaCy 模型未安装或加载失败：
  - 执行：`python -m spacy download xx_sent_ud_sm`
  - 或检查网络/镜像源

- 使用云端 BGE-M3 出现 429（速率限制）：
  - 已内置指数退避与重试，必要时减小批大小（见 `embedding_models.BGE_M3_EmbeddingModel`）


### 适用场景

- RAG 索引构建（将长文切分为语义连贯、大小均匀的块）
- 各类长文本预处理（书籍、技术文档、报告、网页抓取结果）
- 中英混排文本的分句与切分（V3 效果更稳）


### 许可

沿用项目根目录的 LICENSE。


