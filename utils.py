from prompt import SYSTEM_INSTRUCTION, QA_TEMPLATE;
from pathlib import Path
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
import subprocess
import json


LOCAL_BGE_DIR = Path(r"D:\huggingface\models\bge-m3")  # ← 改成你的真实路径
UTTER_JSONL = Path("Resources/utterances/utterances_chunks.jsonl")
FLOWS_JSONL = Path("Resources/flows/flows_chunks.jsonl")
FAISS_DIR = Path("faiss_store")


def _ensure_ollama_model_local(tag: str = "llama3.1"):
    """可选：若本地无该模型则直接报错（而不是尝试下载）"""
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        if tag not in out:
            raise RuntimeError(
                f"Ollama 本地不存在模型 {tag}。请在可联网环境先执行：ollama pull {tag}。"
            )
    except FileNotFoundError:
        raise RuntimeError(
            "未检测到 Ollama，请确认已安装并可在当前环境使用。"
        )


def load_jsonl(path: Path, namespace: str) -> List[Document]:
    docs: List[Document] = []
    if not path.exists():
        return docs
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            text = obj.get("text", "").strip()
            meta = obj.get("metadata", {}) or {}
            meta["namespace"] = namespace
            if text:
                docs.append(Document(page_content=text, metadata=meta))
    return docs

def load_vectorstore(rebuild: bool = False) -> FAISS:
    embed = HuggingFaceEmbeddings(
        model_name=str(LOCAL_BGE_DIR),
        model_kwargs={
            "device": "cpu",  # 或 "cuda"
            # "cache_folder": str(LOCAL_BGE_DIR),  # 可选；进一步指定缓存目录
        },
        encode_kwargs={"normalize_embeddings": True},
    )
    index_file = FAISS_DIR / "index.faiss"
    store_file = FAISS_DIR / "index.pkl"

    docs: List[Document] = []
    docs += load_jsonl(UTTER_JSONL, namespace="utterances")
    docs += load_jsonl(FLOWS_JSONL, namespace="flows")

    if not docs:
        raise FileNotFoundError("未读取到任何文档，请检查 JSONL 路径与内容是否存在 text/metadata 字段。")

    vs = FAISS.from_documents(docs, embed)
    vs.save_local(str(FAISS_DIR))
    return vs