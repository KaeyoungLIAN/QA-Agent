# -*- coding: utf-8 -*-
"""
从两个 JSONL（utterances / flows 的分块结果）构建 bge-m3 + FAISS 向量库。
- 优先从本地路径加载 bge-m3 模型（减少重复下载）
- 读取 JSONL（每行必须包含: text, metadata）
- 用 bge-m3 计算向量，并做 L2 归一化
- 建立 IndexFlatIP（内积）索引并落盘
- 写出 meta.jsonl（与索引向量顺序严格对齐）
- 提供一个检索 demo

依赖:
pip install sentence-transformers faiss-cpu tqdm ujson huggingface_hub
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import ujson as json
from tqdm import tqdm
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# =========================
# 配置
# =========================
JSONL_FILES = [
    "Resources/utterances/utterances_chunks.jsonl",
    "Resources/flows/flows_chunks.jsonl",
]
OUT_DIR = "faiss_store"
LOCAL_MODEL_DIR = r"D:\huggingface/models/bge-m3"  # 本地 bge-m3 模型目录
HF_MODEL_ID = "BAAI/bge-m3"  # 如果本地不存在则从 Hugging Face 下载
BATCH_SIZE = 64
TOP_K = 5
TEXT_FIELD = "text"
META_FIELD = "metadata"


# =========================
# 工具函数
# =========================
def get_model_path(local_dir: str, hf_id: str) -> str:
    """优先使用本地模型目录，如果不存在则自动下载。"""
    from huggingface_hub import snapshot_download
    if os.path.exists(local_dir) and any(
        f in os.listdir(local_dir) for f in ["pytorch_model.bin", "model.safetensors"]
    ):
        print(f"📂 使用本地模型: {local_dir}")
        return local_dir
    else:
        exit()


def load_jsonl(path: str, namespace: str) -> List[Dict[str, Any]]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if TEXT_FIELD not in rec:
                raise KeyError(f"{path} 缺少 '{TEXT_FIELD}' 字段")
            if META_FIELD not in rec or not isinstance(rec[META_FIELD], dict):
                rec[META_FIELD] = {}
            rec[META_FIELD]["namespace"] = namespace
            data.append(rec)
    return data


def embed_chunks(chunks: List[Dict[str, Any]], model_path: str, batch_size: int) -> np.ndarray:
    model = SentenceTransformer(model_path)
    texts = [c[TEXT_FIELD] for c in chunks]
    vecs = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True)
    return np.asarray(vecs, dtype="float32")


def build_faiss(embeddings: np.ndarray) -> faiss.Index:
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)
    return index


def save_sidecar_meta(chunks: List[Dict[str, Any]], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            out = {"id": c.get("id"), "text": c.get(TEXT_FIELD, ""), "metadata": c.get(META_FIELD, {})}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")


def load_sidecar_meta(path: str) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in open(path, "r", encoding="utf-8")]


def demo_search(query: str, index: faiss.Index, meta: List[Dict[str, Any]], model_path: str, top_k: int):
    model = SentenceTransformer(model_path)
    q = model.encode([query], normalize_embeddings=True)
    scores, ids = index.search(np.asarray(q, dtype="float32"), top_k)
    print(f"\n🔎 Query: {query}")
    for rank, (i, s) in enumerate(zip(ids[0], scores[0]), start=1):
        if i == -1:
            continue
        item = meta[i]
        ns = item["metadata"].get("namespace")
        sec = item["metadata"].get("section_path", "")
        src = item["metadata"].get("source", "")
        preview = item["text"][:200].replace("\n", " ")
        print(f"{rank:>2}. [score={s:.4f}] [{ns}] {src} | {sec}")
        print(f"    {preview}{'...' if len(item['text'])>200 else ''}")


# =========================
# 主流程
# =========================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    all_chunks = []
    for p in JSONL_FILES:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"未找到文件：{path.resolve()}")
        ns = path.stem
        all_chunks.extend(load_jsonl(str(path), namespace=ns))

    if not all_chunks:
        raise RuntimeError("未从 JSONL 读取到任何分块。")

    print(f"✅ 加载完成：{len(all_chunks)} 个分块")

    model_path = get_model_path(LOCAL_MODEL_DIR, HF_MODEL_ID)

    embeddings = embed_chunks(all_chunks, model_path, BATCH_SIZE)
    print(f"✅ 嵌入完成：shape={embeddings.shape}")

    index = build_faiss(embeddings)
    faiss_path = os.path.join(OUT_DIR, "index.faiss")
    faiss.write_index(index, faiss_path)
    print(f"✅ FAISS 已保存：{faiss_path}")

    meta_path = os.path.join(OUT_DIR, "meta.jsonl")
    save_sidecar_meta(all_chunks, meta_path)
    print(f"✅ 元数据已保存：{meta_path}")

    print("\n—— 检索 Demo ——")
    index2 = faiss.read_index(faiss_path)
    meta2 = load_sidecar_meta(meta_path)
    demo_search("查询订单状态 怎么说？", index2, meta2, model_path, TOP_K)
    demo_search("申请退货的流程是什么？", index2, meta2, model_path, TOP_K)


if __name__ == "__main__":
    main()
