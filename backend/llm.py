from functools import lru_cache

import openai
from langchain_openai import ChatOpenAI

from backend import config

# global default, switchable at runtime via POST /models
current_model = config.LLM_MODEL


@lru_cache
def get(model):
    return ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=model,
        temperature=0.7,
        max_tokens=512,
    )


def list_models():
    client = openai.OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
    return sorted(m.id for m in client.models.list())


def set_model(model):
    global current_model
    current_model = model
