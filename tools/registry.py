# -*- coding: utf-8 -*-
# agent_tools/registry.py
"""
统一初始化并导出所有工具（供 Agent 注入）。
- 在这里加载向量库并初始化 doc_qa（CRC）。
"""

from typing import List
from langchain_core.tools import BaseTool

from utils import load_vectorstore
from .rag_docqa.tool import init_doc_qa_tool, doc_qa
from .dbtools import (
    orders_get_by_id,
    orders_search_by_phone,
    orders_search_by_email,
    orders_address_update,
)


def init_all_tools() -> List[BaseTool]:
    # 1) 加载/构建向量库，并初始化 doc_qa（封装 CRC）
    vs = load_vectorstore()
    init_doc_qa_tool(vs)

    # 2) 组装全量工具列表
    tools: List[BaseTool] = [
        doc_qa,
        orders_get_by_id,
        orders_search_by_phone,
        orders_search_by_email,
        orders_address_update,
    ]
    return tools
