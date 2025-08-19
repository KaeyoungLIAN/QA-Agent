# -*- coding: utf-8 -*-
# agent_tools/rag_docqa/tool.py
"""
把 CRC 封装成一个可被 Agent 调用的 doc_qa 工具；支持注入外部 facts。
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from .crc_chain import build_crc

# 会话内复用的 CRC 实例
_CRC = None


def init_doc_qa_tool(vectorstore) -> None:
    """
    在应用启动时调用一次：注入向量库并构建 CRC。
    """
    global _CRC
    _CRC = build_crc(vectorstore)


class DocQAInput(BaseModel):
    question: str = Field(..., description="用户的问题")
    facts: Optional[Dict[str, Any]] = Field(
        default=None,
        description="（可选）来自其他工具的结构化事实块，将作为前情提示拼接",
    )


@tool("doc_qa", args_schema=DocQAInput)
def doc_qa(question: str, facts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    基于员工手册/流程/FAQ 的文档检索问答工具。
    用法：当用户问题涉及政策、流程、规则、话术等需要查文档时调用。
    输入：question；如已获得 DB 等外部事实，请放到 facts。
    输出：{"answer": str, "sources": [{"page_content": str, "metadata": {...}}, ...]}
    """
    if _CRC is None:
        return {"error": "doc_qa 未初始化：请先在启动阶段调用 init_doc_qa_tool(vectorstore) 注入向量库。"}

    q = question if not facts else f"【已知事实】{facts}\n【问题】{question}"
    result = _CRC.invoke({"question": q})

    answer = result.get("answer") or ""
    src_docs = result.get("source_documents") or []

    sources: List[Dict[str, Any]] = []
    for d in src_docs:
        sources.append(
            {
                "page_content": getattr(d, "page_content", ""),
                "metadata": getattr(d, "metadata", {}),
            }
        )

    return {"answer": answer, "sources": sources}
