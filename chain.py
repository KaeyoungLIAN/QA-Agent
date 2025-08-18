# -*- coding: utf-8 -*-
from typing import Any
from prompt import SYSTEM_INSTRUCTION
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils import _ensure_ollama_model_local

# 优先使用新版 langchain-ollama；没有则回退到 community 版，避免阻塞
def _get_llm():
    try:
        # 新接口（推荐）
        from langchain_ollama import ChatOllama  # type: ignore
        return ChatOllama(model="llama3.1")
    except Exception:
        # 回退：老接口也能跑，只是会有 deprecation warning
        from langchain_community.llms import Ollama  # type: ignore
        return Ollama(model="llama3.1")

# 历史显式注入的回答 Prompt
ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "{system}\n\n"
        "=== 检索到的资料 ===\n{context}\n====================\n"
        "请基于可用信息作答：1) 简洁分点；2) 不编造；3) 无信息时说明下一步。"
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])

def init_chain(vs: FAISS) -> Any:
    """
    构建带“窗口记忆”的对话式检索链（CRC）。
    - 记忆：仅保留最近 k 轮对话（不做摘要，避免丢细节）
    - Prompt：显式包含 chat_history（MessagesPlaceholder）
    """
    _ensure_ollama_model_local("llama3.1")

    retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    llm = _get_llm()

    memory = ConversationBufferWindowMemory(
        k=6,                           # 仅保留最近 6 轮（人→助理为一轮）
        memory_key="chat_history",
        input_key="question",
        output_key="answer",
        return_messages=True,          # 返回消息列表，便于 CRC 与 Prompt 使用
    )

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        get_chat_history=lambda h: h,  # 原样传递消息列表
        combine_docs_chain_kwargs={
            "prompt": ANSWER_PROMPT.partial(system=SYSTEM_INSTRUCTION)
        },
        return_source_documents=True,
        verbose=False,
    )
    return chain
