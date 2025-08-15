from langchain_ollama import ChatOllama

def get_llm(model="llama3.1", temperature=0):
    return ChatOllama(
        model=model,
        temperature=temperature
    )