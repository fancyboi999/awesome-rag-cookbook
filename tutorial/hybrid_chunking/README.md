# Hybrid Chunking Tutorial (Docling)

本教程演示如何基于 Docling 实现“混合分块（Hybrid Chunking）”，并输出上下文增强文本以用于 RAG。

- 参考文档： [Docling: Hybrid chunking](https://docling-project.github.io/docling/examples/hybrid_chunking/)

## 环境准备（uv）

```bash
uv venv
source .venv/bin/activate
uv pip install docling transformers
```

如使用 `pip`：
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U docling transformers
```

> 若运行时报 `semchunk` 相关错误，可补充安装：
> - `pip install "docling-core[chunking]"`
> - 或使用 OpenAI 计数器：`pip install "docling-core[chunking-openai]"`

## 运行示例脚本

```bash
python tutorial/hybrid_chunking/hybrid_chunking_demo.py \
  --source tutorial/hybrid_chunking/data/wiki.md \
  --print-top 5
```

指定与向量模型一致的分词器（推荐在 RAG 场景保持一致）：
```bash
python tutorial/hybrid_chunking/hybrid_chunking_demo.py \
  --source tutorial/hybrid_chunking/data/wiki.md \
  --tokenizer sentence-transformers/all-MiniLM-L6-v2 \
  --print-top 5
```

> 提示：Docling 的 `HybridChunker` 在部分情况下会触发 transformers 的“序列长度超限”警告，但这是“误报”，详见上方参考文档说明。

## 目录结构

- `tutorial/hybrid_chunking/data/wiki.md`: 示例文档
- `tutorial/hybrid_chunking/hybrid_chunking_demo.py`: 纯 Python 示例
- `tutorial/hybrid_chunking/hybrid_chunking_tutorial.ipynb`: 可交互 Notebook（可选）

## 结果示例
脚本会打印每个分块的原始文本与 `contextualize()` 的上下文增强文本片段，可直接用于嵌入。

---

## 工作原理拆解（基于 `docling/hybrid_chunker.py`）

`HybridChunker` 的核心思想：在“文档结构分块（hierarchical）”基础上，叠加“分词器感知（token-aware）”的精细化切分与合并，使每个分块既保留必要的上下文（标题、说明等），又满足最大 token 限制，最终输出适合检索与嵌入的上下文增强文本。

关键组件与流程：

- 【默认分词器】默认使用 HuggingFace 分词器（`sentence-transformers/all-MiniLM-L6-v2`）。也可显式传入分词器以与嵌入模型对齐。
- 【最大 token】`max_tokens` 由分词器给出（`tokenizer.get_max_tokens()`），用于所有后续控制。
- 【上下文增强】`contextualize(chunk)` 会把标题、说明等上下文串接到文本前，得到“可嵌入”的 enriched 文本；token 统计也基于它。

分块算法三步走：

1) 文档结构切分（Hierarchical）
   - 调用内部的 `HierarchicalChunker` 根据文档结构（标题层级、图表、段落等）产出初始 `DocChunk` 序列。

2) 基于文档项的窗口切分（token-aware by doc items）
   - 针对每个 `DocChunk`，维护一个滑动窗口 `[window_start, window_end]`，尝试逐步增加文档项（doc_items），每次通过 `contextualize()` 计算 token 数。
   - 若超出 `max_tokens`：
     - 如果窗口里只有一个项，先保留它（后续会进入纯文本切分）。
     - 如果有多个项，则把“最后一个项”移到下个窗口，保证当前窗口不超限。
   - 这样得到一组“按文档项”尽量装满但不超限的分块。

3) 纯文本切分（semchunk + 可用 token 动态预算）
   - 对于仍超出 `max_tokens` 的块，计算：
     - `total_len = contextualize(chunk)` 的 token 数
     - `text_len = 仅正文文本` 的 token 数
     - `other_len = total_len - text_len`（标题、说明等上下文开销）
   - 可用预算：`available_length = max_tokens - other_len`
     - 若 `available_length <= 0`：丢弃标题/说明（不记录到该块），重算并按纯文本切分。
     - 否则使用 `semchunk` 基于分词器做纯文本分段，保证每段不超过 `available_length`。

4) 同源上下文合并（Peer merge）
   - 如果开启 `merge_peers=True`：对“上下文元信息一致（如同一标题路径）”的相邻块，尝试合并；合并后再次用 token 计数校验不超限。

设计要点：

- 计数总是以 `contextualize()` 的文本为准，确保“嵌入输入”与“切分约束”一致。
- 优先保留结构化上下文（标题/说明），仅在预算不足时去除。
- 通过“先结构、后文本、再同类合并”的顺序，最大化保留语义与文档脉络。

## 参数与配置

- `tokenizer`
  - 可传入：
    - Docling 的 `BaseTokenizer` 实例（推荐方式）
    - 字符串模型名或 HF `PreTrainedTokenizerBase`（会触发一次兼容层包装，带有弃用提醒）
  - 推荐与嵌入模型保持一致（RAG 检索召回更稳定）。
- `merge_peers: bool`：是否合并元信息一致的相邻小块（默认 `True`）。
- `max_tokens: int`：最大 token；若未显式提供，则读取分词器的默认上限。

兼容层与弃用提醒：
- 传入 `str` 或 HF `AutoTokenizer` 时，会被包装成 Docling 的 `HuggingFaceTokenizer`，并发出 `DeprecationWarning`。这是为了引导用户逐步迁移到 Docling 的 `BaseTokenizer` 抽象。

## 注意事项 / 排错

- 若看到 `semchunk` 相关 `RuntimeError`：安装 `docling-core[chunking]`（或 `chunking-openai`）。
- 若出现 transformers 的“序列长度超限”警告：本示例场景通常为“误报”，详见官方文档说明。
- 若分块过小/过多：
  - 调整所用分词器（不同 tokenizer 的 `max_tokens` 不同）
  - 关闭/开启 `merge_peers` 观察差异
  - 检查输入文档结构（标题层级与段落切分会直接影响初始块）

## 与 RAG 的契合点

- 使用 `contextualize()` 的 enriched 文本作为嵌入输入，能够显著提升召回的“语境正确性”。
- 与嵌入模型共享同一分词器，能避免“计数与召回”不一致导致的边界截断问题。

> 文档与示例参考：[Docling: Hybrid chunking](https://docling-project.github.io/docling/examples/hybrid_chunking/)
