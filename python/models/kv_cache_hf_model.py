# python/kv_cache_hf_model.py

import logging
import os
import torch
from typing import Any, Optional, List, Tuple, Dict
from langchain_core.language_models.llms import LLM
from transformers import AutoTokenizer, AutoModelForCausalLM

from models.model_parameters import HuggingFaceParameters
from models.model_cache import GLOBAL_HF_MODEL_CACHE

# This global dict holds the KV cache state for each chat_id.
KV_CACHES: Dict[str, Tuple] = {}

def reset_all_kv_caches():
    """Clears the KV cache for all conversations. Called when the underlying model changes."""
    global KV_CACHES
    KV_CACHES = {}
    logging.info("All KV Caches have been reset.")

def reset_kv_cache_for_chat(chat_id: str):
    """Clears the KV cache for a specific chat."""
    if chat_id in KV_CACHES:
        del KV_CACHES[chat_id]
        logging.info(f"KV Cache for chat_id {chat_id} has been reset.")

class KVCacheHFModel(LLM):
    """A HuggingFace LLM that uses an external, per-chat_id KV cache."""
    model_name: str
    model: Any = None
    tokenizer: Any = None

    def __init__(self, hf_params: HuggingFaceParameters, **kwargs):
        super().__init__(model_name=hf_params["model_name"], **kwargs)
        self._load_model()

    def _load_model(self):
        """Loads model and tokenizer with authentication."""
        # Read the token from the environment
        hf_token = os.getenv("HF_TOKEN")

        if self.model_name in GLOBAL_HF_MODEL_CACHE:
            logging.info(f"Using cached model for '{self.model_name}'.")
            cached = GLOBAL_HF_MODEL_CACHE[self.model_name]
            self.model, self.tokenizer = cached['model'], cached['tokenizer']
        else:
            logging.info(f"Loading model '{self.model_name}' (not in cache)...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Pass the token to the from_pretrained methods
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=hf_token)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, torch_dtype=torch.bfloat16, token=hf_token
            ).to(device)
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            GLOBAL_HF_MODEL_CACHE[self.model_name] = {'model': self.model, 'tokenizer': self.tokenizer}
        
        logging.info(f"KVCacheHFModel '{self.model_name}' is ready.")
        
    @property
    def _llm_type(self) -> str:
        return "KVCacheHFModel"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, chat_id: Optional[str] = None, **kwargs: Any) -> str:
        if not chat_id: raise ValueError("chat_id is required for KV Caching.")
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        past_key_values = KV_CACHES.get(chat_id)
        
        outputs = self.model.generate(
            **inputs, max_new_tokens=512, use_cache=True, past_key_values=past_key_values,
            return_dict_in_generate=True, **kwargs
        )
        
        KV_CACHES[chat_id] = outputs.past_key_values
        response_text = self.tokenizer.decode(outputs.sequences[0, inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
        return response_text