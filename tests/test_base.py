from easyharness import Agent, ModelConfig

agent = Agent(
    model=ModelConfig(
        model="deepseek-v4-pro",
        api_key="sk-43f50b930abe4e97ac3292a66d5c7303",
        base_url="https://api.deepseek.com/v1"
    ),
    system_prompt="你是一个严谨的 copilot。",
    enable_fileglide=True
)

print(agent.run(r"你好呀，你叫什么名字"))
