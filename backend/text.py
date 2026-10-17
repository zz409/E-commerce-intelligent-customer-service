import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

BACKEND_DIR = Path(__file__).resolve().parent

load_dotenv(BACKEND_DIR / ".env")

DATABASE_PATH = BACKEND_DIR / "checkpoints.sqlite"


def main():
    model = init_chat_model(
        model="qwen3.8-max",
        model_provider="openai",
        api_key=os.environ["QWEN_API_KEY"],
        base_url="https://maas.qianwenaiapi.com/compatible-mode/v1",
    )

    config = {
        "configurable": {
            "thread_id": "1"
        }
    }

    with SqliteSaver.from_conn_string(
        str(DATABASE_PATH)
    ) as checkpointer:
        agent = create_agent(
            model=model,
            tools=[],
            system_prompt="你是一个智能助手，请使用中文回答。",
            checkpointer=checkpointer,
        )

        # 循环必须放在 with 内部
        while True:
            user_input = input("你：").strip()

            if not user_input:
                continue

            if user_input == "/exit":
                break

            if user_input == "/history":
                snapshot = agent.get_state(config)

                for message in snapshot.values.get("messages", []):
                    print(f"[{message.type}] {message.content}")

                print()
                continue

            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": user_input,
                        }
                    ]
                },
                config=config,
            )

            print(f"\n客服：{result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()