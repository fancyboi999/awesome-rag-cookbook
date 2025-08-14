## FAISS 教程：从入门到进阶（FlatL2 / IVF / HNSW、文本嵌入、持久化与可视化）

本目录包含交互式 Notebook `faiss_tutorial.ipynb`，通过可运行的示例带你快速上手并系统掌握 FAISS：

- 精确与近似检索：`IndexFlatL2`、`IndexIVFFlat`、`IndexHNSWFlat`
- 文本向量搜索：`sentence-transformers`（示例使用 `BAAI/bge-m3`）
- 指标与可视化：查询耗时、R@5 召回、加速比对比
- 索引工程能力：批量构建、ID 映射（`IndexIDMap`）、索引持久化（`faiss.write_index/read_index`）
- 中文可视化：自动配置 Matplotlib 中文字体（Notebook 内已处理）

### 目录结构
- `faiss_tutorial.ipynb`：完整教程（交互式）。

### 环境准备（推荐使用 uv）
建议在 `tutorial/` 目录下创建专用虚拟环境（供所有教程共用）。

```bash
cd /Users/mini/Desktop/awesome-rag-cookbook/tutorial
uv venv
source .venv/bin/activate
uv pip install --upgrade pip

# 基础依赖
uv pip install numpy matplotlib jupyter ipywidgets scipy

# 安装 FAISS（CPU）
uv pip install faiss-cpu

# 可选：安装 FAISS（GPU，需要已配置 CUDA）
# uv pip install faiss-gpu

# 文本嵌入（用于语义搜索示例）
uv pip install sentence-transformers
```

提示：若在 macOS 上遇到 `faiss-cpu` 安装问题，可优先尝试上述 wheel；若仍失败，可考虑使用 Conda（`conda install -c conda-forge faiss-cpu`）。

### 运行方式
交互式运行 Notebook：

```bash
cd /Users/mini/Desktop/awesome-rag-cookbook/tutorial/vector_search/faiss
jupyter notebook faiss_tutorial.ipynb
```

首次运行“文本向量搜索”单元时，会自动从 Hugging Face 下载 `BAAI/bge-m3` 模型，需确保网络可达。

### 教程要点
- 精确检索与近似检索对比：
  - `IndexFlatL2`（精确、无训练）
  - `IndexIVFFlat`（聚类分桶 + 近似、需先 `train`）
  - `IndexHNSWFlat`（图索引、近似、构建时完成）
- 可视化指标：
  - 平均查询时间（含对数坐标）
  - R@5 召回率（与 `FlatL2` 的前 5 结果对齐度）
  - 相对加速比（相对于 `FlatL2`）
- 工程实践：
  - 批量生成与添加向量（大规模示例）
  - 自定义 ID 与元数据（`IndexIDMap` + 外部 `metadata.json`）
  - 索引持久化（`faiss.write_index` / `faiss.read_index`）

### 常见问题
- 中文字体显示异常：Notebook 已提供自动降级的中文字体配置；若仍缺字，可在系统安装中文字体后重启内核。
- IProgress/Tqdm 告警：已安装 `ipywidgets` 可消除大部分告警，不影响运行。
- GPU 环境：仅在已正确安装 CUDA 和对应 PyTorch 的前提下安装 `faiss-gpu`。

### 参考
- [Faiss 官方文档](https://github.com/facebookresearch/faiss)
- [sentence-transformers 文档](https://www.sbert.net/)


