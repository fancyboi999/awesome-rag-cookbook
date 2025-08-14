## 迟分（Late Chunking）教程

本教程演示一种高效的文本切分与向量化策略：先对“整篇长文”进行一次编码，再在 token 级隐藏状态上按句/段做“后切分”，直接池化得到每个块的向量。这与传统“先切分、再逐块编码”的流程相对。

适配脚本位于本目录：
- `test_late_chunking.py`：核心实现与基本示例
- `run_test.py`：运行对比测试（传统分块 vs 迟分）
- `test_hongloumeng.py`：在《红楼梦》文本上的更完整评测（性能与检索质量）

### 原理概述

迟分（Late Chunking）的关键思想：
1) 使用同一编码器对“完整文档”进行一次前向推理，拿到 token 级隐藏状态 `H ∈ R^{L×D}`（`L` 为序列长度，`D` 为隐层维度）。
2) 依据句子/标点或 token 边界，将 `[1, L-1]` 的 token 索引切分为若干区间（块）。
3) 对每个块内的隐藏状态做掩码平均池化（或其它池化策略，如 max/attention pool），得到块向量。
4) 查询时单独编码 query，计算与各块向量的相似度并排序。

与传统方法相比，迟分避免了“对每个块都重复跑一遍编码器”的开销，尤其在文档很长、块很多时优势明显。同时，块向量来自“统一上下文”的一次编码，更好保留全局语境的一致性。

### 对比：迟分 vs 传统分块

- **性能**：
  - 迟分：整文一次编码，块级仅做张量切片与池化，GPU/CPU 开销显著降低。
  - 传统：每个块独立调用编码器，块数越多，时间线性增长。

- **上下文一致性**：
  - 迟分：所有块的向量来自同一上下文的一次前向，语义坐标系一致。
  - 传统：不同块独立编码，边界处可能割裂，跨块语境难以对齐。

- **模型适配度**：
  - 迟分：块向量是对 token 隐藏状态的“二次池化”，可能与模型原生的句向量策略有差异；需注意池化方式的选择。
  - 传统：直接采用模型对短文本的默认句向量/CLS 向量，路径更“标准”。

- **内存与长度限制**：
  - 迟分：需要一次性容纳整文（或长片段）到模型最大序列长度与显存/内存中；超长文需分段处理。
  - 传统：天然分块，较少触及单次前向的长度/显存瓶颈。

- **实现复杂度**：
  - 迟分：需通过 `offset_mapping` 准确映射 token 到原文字符边界；实现更复杂。
  - 传统：切分+逐块编码，逻辑直观。

总结：当单篇文档长度在编码器可承载范围内且需要处理大量块时，迟分常具有显著的吞吐优势与更稳定的一致性；当文档远超上下文窗口或资源受限时，传统分块更稳妥。

### 环境准备

建议 Python 3.10+。

使用 `uv` 管理虚拟环境：
```bash
uv venv
source .venv/bin/activate
# 安装依赖（CPU 环境示例）
uv pip install --upgrade pip
uv pip install "torch" "transformers" "numpy"
```

说明：如果需要 GPU/Apple Silicon 的特定构建，请参考 PyTorch 官方安装指引选择合适的安装命令。

### 模型准备（BAAI/bge-m3）

本教程默认使用 `BAAI/bge-m3`。不同脚本对于模型位置的要求不同：
- `test_late_chunking.py`：可直接使用 Hub ID（会自动从 Hugging Face 下载并缓存）。
- `run_test.py` 与 `test_hongloumeng.py`：包含本地路径存在性检查，期望在项目根目录存在目录 `BAAI/bge-m3`。

若需要在项目根准备本地目录 `BAAI/bge-m3`，可运行：
```bash
python - <<'PY'
from transformers import AutoTokenizer, AutoModel
import os
save_dir = "BAAI/bge-m3"
os.makedirs(save_dir, exist_ok=True)
tok = AutoTokenizer.from_pretrained("BAAI/bge-m3")
tok.save_pretrained(save_dir)
mdl = AutoModel.from_pretrained("BAAI/bge-m3")
mdl.save_pretrained(save_dir)
print("Model saved to:", save_dir)
PY
```

### 数据准备（可选，《红楼梦》评测）

`test_hongloumeng.py` 默认从 `project_root/datas/test_late_chunking/红楼梦.txt` 读取文本。但本仓库示例文件位于：
- `tutorial/chunk_strategy/late_chunking/红楼梦.txt`

二选一：
- 将文件拷贝/链接到脚本期望路径：`datas/test_late_chunking/红楼梦.txt`；或
- 修改 `test_hongloumeng.py` 中 `load_hongloumeng_text()` 的路径，使之指向 `tutorial/chunk_strategy/late_chunking/红楼梦.txt`。

另外，这两个脚本中包含绝对路径：
- `run_test.py` 与 `test_hongloumeng.py` 顶部的 `project_root = "/Users/mini/Desktop/awesome-rag-cookbook"`

请根据你的本地仓库绝对路径进行修改。

### 如何运行

1) 基础功能与 API 演示：
```bash
python tutorial/chunk_strategy/late_chunking/test_late_chunking.py
```

2) 传统分块 vs 迟分 对比（小示例）：
```bash
python tutorial/chunk_strategy/late_chunking/run_test.py
```

3) 《红楼梦》评测（性能与检索质量对比）：
```bash
python tutorial/chunk_strategy/late_chunking/test_hongloumeng.py
```

运行期望：
- 打印“整文编码 → 切分 → 池化”步骤与块统计
- 打印查询的 Top-K 检索结果（相似度分数与文本片段预览）
- 在《红楼梦》脚本中输出耗时对比与块长度统计

### 关键实现要点（对应代码）

- `LateChunkingProcessor.encode_document(text)`：
  - 以最大上下文窗口对整篇文本做一次前向，返回 `hidden_states`、`input_ids`、`attention_mask`。

- `LateChunkingProcessor.create_chunks_by_sentences(text, chunk_size)`：
  - 通过 `tokenizer(..., return_offsets_mapping=True)` 拿到 token 到字符的映射，根据标点/边界尽量在句末切分，获得 `(chunk_text, start_token, end_token)`。

- `LateChunkingProcessor.extract_chunk_embeddings(hidden_states, attention_mask, chunks)`：
  - 对区间 `[start_token, end_token)` 的隐藏状态按掩码做平均池化，归一化得到块向量。

- `LateChunkingProcessor.similarity_search(query, chunk_infos, top_k)`：
  - 独立编码查询，计算查询向量与各块向量的点积相似度并排序。

### 常见问题与建议

- **显存/内存不足或超出模型最大长度**：
  - 减小 `max_length` 或对超长文先分大段再做迟分；或切换至传统分块。
  - 在 CPU 或 Apple Silicon 上，长文本前向可能较慢，建议先用较短样例验证流程。

- **检索质量欠佳**：
  - 调整块大小（字符/token 维度均可尝试）；
  - 尝试不同池化策略（当前为平均池化）；
  - 使用更适配检索任务的编码模型。

- **路径与依赖问题**：
  - 确保绝对路径 `project_root` 与模型目录 `BAAI/bge-m3` 设置正确；
  - 使用 `uv` 或 `pip` 正确安装 `torch/transformers/numpy`，并确保 Python 版本兼容。

