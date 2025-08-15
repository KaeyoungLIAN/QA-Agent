import json
import uuid
from pathlib import Path
from typing import List
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# =========================
# 配置（按需修改）
# =========================
MD_FILE = "Resources/flows/flows_wo_toc.md"
OUT_JSONL = "Resources/flows/flows_chunks.jsonl"
HEADERS = [("#","h1"),("##","h2"),("###","h3")]
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 120
SEPARATORS = ["\n```", "```", "\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", "，", ",", " ", ""]
USE_TOKEN_LENGTH = False            # 如用 OpenAI/Claude 再改 True（需要 tiktoken）

# 分隔符由“粗到细”，递归回退，尽量不破坏语义边界
SEPARATORS = [
    "\n\n", "\n",
    "。", "！", "？", ".", "!", "?", "；", ";",
    "，", ",", " ",
    ""  # 最兜底，必要时按字符切
]


def tiktoken_len(text: str) -> int:
    """可选：按 token 计长度（适合 OpenAI/Claude），默认不用。"""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def build_markdown_chunks(
    md_text: str,
    source_name: str,
    chunk_size: int,
    chunk_overlap: int,
    headers,
    separators: List[str],
    use_token_len: bool = False
):
    """Markdown 标题感知切分 + 递归字符细切 + 元数据整理"""
    # 1) 标题感知切分
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers,
        strip_headers=False
    )
    docs = header_splitter.split_text(md_text)  # List[Document], metadata 含 h1/h2/h3

    # 2) 递归字符分块（控制长度 & 重叠）
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=(tiktoken_len if use_token_len else len),
        separators=separators,
    )

    chunks = []
    for d in docs:
        pieces = splitter.split_documents([d])
        for p in pieces:
            h1 = p.metadata.get("h1", "")
            h2 = p.metadata.get("h2", "")
            h3 = p.metadata.get("h3", "")
            p.metadata["section_path"] = " > ".join([x for x in (h1, h2, h3) if x])
            p.metadata["source"] = source_name
            chunks.append(p)
    return chunks


def export_jsonl(chunks, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for d in chunks:
            rec = {
                "id": str(uuid.uuid4()),
                "text": d.page_content,
                "metadata": d.metadata,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    md_path = Path(MD_FILE)
    if not md_path.exists():
        raise FileNotFoundError(f"找不到 Markdown 文件：{md_path.resolve()}")

    md_text = md_path.read_text(encoding="utf-8")

    chunks = build_markdown_chunks(
        md_text=md_text,
        source_name=md_path.name,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        headers=HEADERS,
        separators=SEPARATORS,
        use_token_len=USE_TOKEN_LENGTH,
    )

    export_jsonl(chunks, Path(OUT_JSONL))

    total_chars = sum(len(c.page_content) for c in chunks)
    print("✅ 分块完成")
    print(f"文件：{md_path.name}")
    print(f"块数：{len(chunks)}")
    print(f"总字符数（含重叠）：{total_chars}")
    print(f"输出：{OUT_JSONL}")

    # 展示一个样例块
    if chunks:
        sample = chunks[0]
        print("\n— 样例块预览 —")
        print("section_path:", sample.metadata.get("section_path", ""))
        print(sample.page_content[:300].strip(), "..." if len(sample.page_content) > 300 else "")


if __name__ == "__main__":
    main()
