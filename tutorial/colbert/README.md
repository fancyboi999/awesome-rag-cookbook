## ColBERT 教程：基于 BGE-M3 的 Token 级检索与残差压缩

本目录演示如何使用 BAAI 的 BGE-M3 模型生成 ColBERT 风格的 token 级向量，并实现一种简化版的“残差压缩”方案（K-Means 质心 + 残差量化），以在较小精度损失下显著降低存储占用，同时验证压缩前后检索相关性得分的一致性。

### 目录结构
- `colbertv1_tutorial.py`：最小示例，演示 BGE-M3 的 `dense_vecs` 与 `colbert_vecs` 的相似度计算方式，对比原始点积、归一化后点积以及 `model.colbert_score` 的结果。
- `colbertv2_tutorial.py`：端到端示例（脚本版）。完成文档向量生成 → 残差压缩 → 解压重建 → 质量与相关性评估 → 模型状态持久化。
- `colbertv2_tutorial.ipynb`：与脚本一致的 Notebook 版本，便于交互式学习与可视化。
- `colbert_compressor_bge_m3.pkl`：示例运行后保存的压缩器状态（质心与量化范围等），可在推理阶段复用。

### 教程要点
- 使用 `FlagEmbedding.BGEM3FlagModel` 生成 token 级向量（`colbert_vecs`），并以 ColBERT 的 MaxSim 思路计算查询-文档相关性：对查询每个 token，在文档所有 token 中取最大相似度，再求和。
- 实现简化的残差压缩：
  - 用 K-Means 学习全局质心；
  - 对每个 token 向量只保存最近质心索引和与其的残差；
  - 将残差按全局范围线性量化为 8bit；
  - 解压时以“质心 + 反量化残差”重建。
- 评估指标：
  - 压缩比（原始字节 / 压缩后字节）；
  - 重建误差（MSE）；
  - 压缩前后相关性得分的相对差异（用于检验检索排序稳定性）。

### 环境准备（优先使用 uv）
建议在 `tutorial/` 下创建虚拟环境并安装依赖。

```bash
cd /Users/mini/Desktop/awesome-rag-cookbook/tutorial
uv venv
source .venv/bin/activate
uv pip install --upgrade pip
uv pip install numpy scikit-learn FlagEmbedding ipywidgets jupyter
# 按需安装/配置 PyTorch（根据平台选择安装指令）
# 参考 https://pytorch.org/get-started/locally/
```

如需消除 Notebook 中的 tqdm IProgress 告警，可安装并启用 ipywidgets：
```bash
uv pip install ipywidgets
``` 

### 运行方式
1) 运行最小示例（相似度计算对比）：
```bash
cd /Users/mini/Desktop/awesome-rag-cookbook/tutorial/colbert
python colbertv1_tutorial.py
```

2) 运行端到端压缩示例（脚本版）：
```bash
cd /Users/mini/Desktop/awesome-rag-cookbook/tutorial/colbert
python colbertv2_tutorial.py
```

3) 交互式运行（Notebook 版）：
```bash
cd /Users/mini/Desktop/awesome-rag-cookbook/tutorial/colbert
jupyter notebook colbertv2_tutorial.ipynb
```

### 期待结果（示例）
- v1 脚本会打印：
  - `dense_vecs` 形状与任意两句 `dense` 向量的余弦相似度；
  - `colbert_vecs` 的 MaxSim 相关性（原始点积 vs 归一化点积 vs `model.colbert_score`）。
- v2 脚本会打印：
  - 生成的文档数量与原始未压缩大小；
  - 训练 K-Means 的向量规模与维度、残差范围；
  - 压缩后总大小与压缩比（示例约 4x）；
  - 重建均方误差（MSE，理想情况接近 0）；
  - 压缩前后相关性得分的相对差异（通常极小，< 0.1%）。
  - 并保存压缩器状态为 `colbert_compressor_bge_m3.pkl`。

### 关键实现与验证
- 归一化相似度：为稳定 MaxSim，示例对每个 token 向量进行 L2 归一化再点积。
- K-Means 自适应：若样本量小于设定质心数，自动下调以避免不必要的空簇与数值问题。
- 残差量化：使用全局 `r_min/r_max` 做线性量化（8bit），并在反量化时恢复；若范围为 0 则安全降级为全 0 残差。
- 评估一致性：同一原始查询向量分别与“原始文档向量”和“重建文档向量”计算得分，对比相对差异评估排序稳定性。

### 在推理阶段复用压缩器
`colbertv2_tutorial.py`/`.ipynb` 已提供 `ResidualCompressor.save/load`。推理时可：
1) 加载已保存的压缩器状态；
2) 对离线压缩过的文档向量进行解压重建；
3) 与在线生成的查询向量做 MaxSim 相关性计算。

伪代码示意：
```python
compressor = ResidualCompressor().load('colbert_compressor_bge_m3.pkl')
# 假设已持久化了每个文档的 {centroids_idx, quantized}
doc_vectors = compressor.decompress([stored_doc])[0]
# 生成查询向量并计算相关性
output = model.encode([query], return_colbert_vecs=True)
query_vec = np.array(output['colbert_vecs'][0], dtype=np.float32)
# 计算 MaxSim（参考脚本内 compute_similarity）
```

### 常见问题
- IProgress/Tqdm 告警：安装 `ipywidgets` 并在 Jupyter 中启用；或忽略不影响结果。
- Tokenizers 并行告警：可设置 `export TOKENIZERS_PARALLELISM=false` 以消除提示。
- 质心数选择：`n_centroids` 过大时收益递减且训练变慢；建议从 64/128 起步，根据语料规模调优。
- 精度与压缩比权衡：
  - 提升 `bits`（例如 8→12/16）可降低误差、增大体积；
  - 增大 `n_centroids` 通常能降低残差、提升重建质量，但训练和存储索引成本提升。

### 自定义与扩展
- 替换示例文档为你的业务语料，验证压缩比与检索效果。
- 尝试 per-dimension 或 per-cluster 的量化范围以进一步压缩；
- 引入乘积量化（PQ）或 OPQ，与本教程的残差量化做对比实验；
- 将压缩与 ANN 索引（如 FAISS/HNSW）结合，评估端到端召回与时延表现。

### 许可
遵循仓库根目录的 `LICENSE`。