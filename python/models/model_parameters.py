# model_parameters.py

from typing import List, Optional, TypedDict

# Define a TypedDict for Hugging Face specific parameters
class HuggingFaceParameters(TypedDict):
    model_name: str      # e.g., "meta-llama/Llama-3.1-8B-Instruct"
    use_kv_cache: bool   # e.g., True or False

# Define a TypedDict for generalized model parameters
class ModelParameters(TypedDict):
    framework_type: str  # e.g., "LangChain"
    backend: str         # e.g., "HuggingFace", "vLLM", "OpenAI"
    model_version: str   # e.g., "Base", "RAG"
    hf_params: Optional[HuggingFaceParameters]