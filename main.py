from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from tools.registry import init_all_tools

def bootstrap_agent() -> AgentExecutor:
    tools = init_all_tools()
    llm = ChatOllama(model="llama3.1", temperature=0)

    # ✅ 关键改动：去掉 {format_instructions}，改为“写死”的 ReAct 输出格式说明
    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "你是一个智能客服助理，可以使用工具解决问题。\n\n"
        "可用工具：\n{tools}\n\n"
        "使用规则：\n"
        "1) 涉及政策/流程/话术 → 调用 doc_qa（如前一步拿到 DB 事实，请一并提供给 doc_qa）。\n"
        "2) 涉及订单信息 → 先调订单工具（按 id/phone/email），拿到结构化事实后再用 doc_qa 生成合规答复。\n"
        "3) 涉及修改操作（如地址） → 先征得用户确认，再调用写库工具。\n"
        "4) 回答必须基于工具返回内容，不得编造。\n"
        "你可以使用的工具名：{tool_names}\n\n"
        "【严格的输出格式要求】当需要调用工具时，必须严格使用以下格式：\n"
        "Thought: <你的思考>\n"
        "Action: <工具名>\n"
        "Action Input: {{\"order_id\": \"OD2408150001\"}}\n"  # 👈 这里用双花括号
        "（拿到工具结果后继续）\n"
        "Observation: <工具返回内容>\n"
        "...（若需要可多轮 Thought/Action/Action Input/Observation）\n"
        "当你准备给用户最终回复时，使用：\n"
        "Final Answer: <面向用户的最终答案>\n"),
        ("human", "{input}"),
        ("assistant", "{agent_scratchpad}"),
    ])


    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    # ✅ 关键改动：给执行器开启解析容错，模型偶尔格式不严时自动重试
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    return executor

if __name__ == "__main__":
    executor = bootstrap_agent()
    print("🤖 智能客服已启动（输入 '退出' 结束）\n")
    while True:
        q = input("用户：")
        if q.strip().lower() in ["退出", "exit", "quit"]:
            break
        resp = executor.invoke({"input": q})
        print("助理：", resp["output"], "\n")
