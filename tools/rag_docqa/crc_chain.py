# -*- coding: utf-8 -*-
# agent_tools/rag_docqa/crc_chain.py
"""
把你现有的 ConversationalRetrievalChain 独立成“构建函数”，供 doc_qa 工具复用。
"""

from typing import Any
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from prompt import SYSTEM_INSTRUCTION
from utils import _ensure_ollama_model_local


def _get_llm():
    """优先新版 langchain_ollama，失败则回退 community 版。"""
    try:
        from langchain_ollama import ChatOllama  # type: ignore
        return ChatOllama(model="llama3.1", temperature=0)
    except Exception:
        from langchain_community.llms import Ollama  # type: ignore
        return Ollama(model="llama3.1")


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "{system}\n\n"
            "=== 检索到的资料 ===\n{context}\n====================\n"
            "请基于可用信息作答：1) 简洁分点；2) 不编造；3) 无信息时说明下一步。"
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ]
)


def build_crc(vs: FAISS) -> Any:
    """
    基于给定向量库构建 ConversationalRetrievalChain。
    """
    _ensure_ollama_model_local("llama3.1")

    retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    llm = _get_llm()

    memory = ConversationBufferWindowMemory(
        k=6,
        memory_key="chat_history",
        input_key="question",
        output_key="answer",
        return_messages=True,
    )

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        get_chat_history=lambda h: h,
        combine_docs_chain_kwargs={"prompt": ANSWER_PROMPT.partial(system=SYSTEM_INSTRUCTION)},
        return_source_documents=True,
        verbose=False,
    )
    return chain
