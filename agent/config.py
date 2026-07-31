import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL_NAME = "gpt-5.6"

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY was not found. Add it to the project's .env file."
    )

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=api_key,
    reasoning_effort="none",
)