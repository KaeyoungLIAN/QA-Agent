# -*- coding: utf-8 -*-
"""
最小可用（MVP）的 LangChain+RAG（完全离线版）
- 仅使用你本地已下载的 BGE-M3（sentence-transformers 格式）与 Ollama 模型
- 绝不联网；若缺文件则直接报错（而不是尝试下载）

使用步骤：
1) 修改 LOCAL_BGE_DIR 为你本地 BGE-M3 的目录（需包含 modules.json / config.json / tokenizer.json / sentencepiece* 等）
2) 确认本地已存在 Ollama 模型（例如：llama3.1）。可在联网环境提前执行一次：`ollama pull llama3.1`
3) 首次构建向量库：
   python LangChain_RAG_MVP_offline.py --build
4) 交互问答：
   python LangChain_RAG_MVP_offline.py

依赖：
  pip install -U langchain langchain-community langchain-core langchain-text-splitters
  pip install -U faiss-cpu sentence-transformers
"""

import os
import argparse
import json
import subprocess
from pathlib import Path
from typing import List

# —— 完全离线：阻断一切 HuggingFace/Transformers 在线访问 ——
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
# 如需统一缓存目录（可选）
# os.environ["HF_HOME"] = r"D:\huggingface\cache"
# os.environ["TRANSFORMERS_CACHE"] = r"D:\huggingface\cache\transformers"
# os.environ["SENTENCE_TRANSFORMERS_HOME"] = r"D:\huggingface\cache\sentence-transformers"

# ============ 本地模型路径（按你的机器修改） ============
# 必须是 Sentence-Transformers 打包结构（含 modules.json）
LOCAL_BGE_DIR = Path(r"D:\huggingface\models\bge-m3")  # ← 改成你的真实路径

if not LOCAL_BGE_DIR.exists() or not (LOCAL_BGE_DIR / "modules.json").exists():
    raise FileNotFoundError(
        f"未找到本地 BGE-M3（sentence-transformers）目录：{LOCAL_BGE_DIR}\n"
        f"请把 LOCAL_BGE_DIR 改成你的真实路径，并确保目录内包含 modules.json / config.json / tokenizer.json / sentencepiece* 等文件。"
    )

# ============ 路径配置（按你仓库结构调整） ============
UTTER_JSONL = Path("Resources/utterances/utterances_chunks.jsonl")
FLOWS_JSONL = Path("Resources/flows/flows_chunks.jsonl")
FAISS_DIR = Path("faiss_store_langchain")

# ============ LangChain 组件 ============
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate


# ============ 数据加载 ============
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


# ============ 向量库构建 / 加载 ============
def build_or_load_vectorstore(rebuild: bool = False) -> FAISS:
    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    # 仅从本地目录加载（不给仓库名，避免联网）
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

    if not rebuild and index_file.exists() and store_file.exists():
        return FAISS.load_local(str(FAISS_DIR), embed, allow_dangerous_deserialization=True)

    docs: List[Document] = []
    docs += load_jsonl(UTTER_JSONL, namespace="utterances")
    docs += load_jsonl(FLOWS_JSONL, namespace="flows")

    if not docs:
        raise FileNotFoundError("未读取到任何文档，请检查 JSONL 路径与内容是否存在 text/metadata 字段。")

    vs = FAISS.from_documents(docs, embed)
    vs.save_local(str(FAISS_DIR))
    return vs


# ============ 检索增强问答链 ============
SYSTEM_INSTRUCTION = (
    "你是一个严谨的检索型客服助手。严格依据提供的上下文回答；"
    "模版中的回答是一种很好的参考，你可以根据模版进行回答，也可以根据模版进行修改，但不要完全照搬模版。"
    "你需要根据客户的语气和问题选择合适的模版风格："
    "  - 如果用户语气平和、问题中性，请使用 neutral 模版。"
    "  - 如果用户表达了焦虑、生气、失望等情绪，请使用 empathetic 模版，并在回答中适当加入安抚、理解性的语气，例如“我理解您的感受”。"
    "  - 如果问题涉及正式场合（如发票、合同、政策），请选择 formal 模版，用更正式、专业的语气回答。"
    "在回答时，可以灵活调整模版内容，使其更自然、更符合人类客服口吻，允许加入诸如“您好”“感谢您的耐心”等礼貌用语。"
    "若上下文中没有可直接套用的模板，请进行简洁、明确的回答；"
    "如果资料不足，请直接说“我不确定”。"
)


QA_TEMPLATE = """
{system}

以下是检索到的资料片段（可能摘录，含 flows / utterances / rules 等）：
{context}

问题：{question}

请遵循以下优先级作答：
1) 若资料中出现可直接使用的『话术模板』（尤其是 neutral 版本），可以套用模版进行回答。；
2) 若没有现成模板，再基于资料进行简洁、明确的回答；
3) 若资料不足以支持答案，请说“我不确定”。

只输出答案正文，不要解释思路。
"""


PROMPT = PromptTemplate(
    template=QA_TEMPLATE,
    input_variables=["system", "context", "question"],
)


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


def make_qa_chain(vs: FAISS):
    # 确保本地已有 LLM（否则直接抛错，避免联网）
    _ensure_ollama_model_local("llama3.1")

    retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    llm = Ollama(model="llama3.1")

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={
            "prompt": PROMPT.partial(system=SYSTEM_INSTRUCTION),
        },
        return_source_documents=True,
    )
    return chain


# ============ CLI 交互 ============
def pretty_sources(docs: List[Document]) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        ns = d.metadata.get("namespace", "?")
        src = d.metadata.get("source") or d.metadata.get("path") or d.metadata.get("file") or "unknown"
        preview = d.page_content[:160].replace("\n", " ") + ("..." if len(d.page_content) > 160 else "")
        lines.append(f"[{i}] <{ns}> {src}\n    {preview}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="强制重新构建向量库")
    args = parser.parse_args()

    vs = build_or_load_vectorstore(rebuild=args.build)
    qa = make_qa_chain(vs)

    print("\n✔ RAG（离线）已就绪。输入问题进行检索问答，输入`退出`结束。\n")
    while True:
        q = input("你：").strip()
        if not q:
            continue
        if q in {"退出", "exit", "quit", "q"}:
            break
        resp = qa.invoke({"query": q})  # RetrievalQA 接口字段为 "query"
        answer = resp.get("result", "(无结果)")
        sources = resp.get("source_documents", [])

        print("\n答复：\n" + answer.strip() + "\n")
        # if sources:
        #     print("依据（Top-K）：\n" + pretty_sources(sources) + "\n")


if __name__ == "__main__":
    main()
