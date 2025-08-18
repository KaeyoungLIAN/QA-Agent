# -*- coding: utf-8 -*-
from chain import init_chain
from utils import load_vectorstore

EXIT_WORDS = {"退出", "exit", "quit", "q"}

def main():
    vs = load_vectorstore(rebuild=False)
    qa = init_chain(vs)

    print("\n✔ RAG（离线）已就绪。输入问题进行检索问答，输入`退出`结束。\n")
    while True:
        try:
            q = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q in EXIT_WORDS:
            break

        resp = qa.invoke({"question": q})
        answer = (resp.get("answer") or resp.get("result") or "").strip()
        if not answer:
            answer = "抱歉，这个问题我暂时没有足够信息作答。要不要换个问法，或提供更多线索？"

        print("\n答复：\n" + answer + "\n")

if __name__ == "__main__":
    main()
