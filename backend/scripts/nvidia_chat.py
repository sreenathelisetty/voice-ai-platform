import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(
    model="openai/gpt-oss-20b",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    temperature=1,
    top_p=1,
    max_tokens=4096,
)

response = llm.invoke([HumanMessage(content="")])

if hasattr(response, "additional_kwargs"):
    reasoning = response.additional_kwargs.get("reasoning_content")
    if reasoning:
        print(reasoning)

print(response.content)
