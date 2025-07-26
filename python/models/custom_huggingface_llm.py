import logging
from typing import Any, Optional, List, Dict, Tuple, TypedDict
import torch
from langchain_core.language_models.llms import LLM
from transformers import AutoTokenizer, AutoModelForCausalLM

from models.model_parameters import HuggingFaceParameters
from models.model_cache import GLOBAL_HF_MODEL_CACHE # Import the global cache

# Moved from chat_manager.py
class HuggingFaceParameters(TypedDict):
    model_name: str      # e.g., "meta-llama/Llama-3.1-8B-Instruct"
    use_kv_cache: bool   # e.g., True or False

class CustomHuggingFaceLLM(LLM):
    """A customizable HuggingFace LLM that supports various options, including explicit KV cache management for persistent context."""
    model_name: str
    use_kv_cache: bool
    _model: Any = None
    _tokenizer: Any = None
    _past_key_values: Optional[Tuple[Tuple[torch.Tensor, torch.Tensor], ...]] = None

    def __init__(self, hf_params: HuggingFaceParameters, **kwargs):
        """Initializes and loads a dedicated model instance based on provided HuggingFace parameters."""
        # Set model parameters first
        model_name = hf_params["model_name"]
        use_kv_cache = hf_params["use_kv_cache"]
        
        # Initialize Pydantic model with the parameters
        super().__init__(model_name=model_name, use_kv_cache=use_kv_cache, **kwargs)
        
        # Load model and tokenizer
        self._load_model()

    def _load_model(self):
        """Load or retrieve the model and tokenizer from cache or HuggingFace Hub."""
        try:
            if self.model_name in GLOBAL_HF_MODEL_CACHE:
                logging.info(f"Using cached model and tokenizer for '{self.model_name}'.")
                self._model = GLOBAL_HF_MODEL_CACHE[self.model_name]['model']
                self._tokenizer = GLOBAL_HF_MODEL_CACHE[self.model_name]['tokenizer']
            else:
                logging.info(f"Loading model '{self.model_name}' for CustomHuggingFaceLLM instance (not in cache)...")
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if device == "cuda":
                    logging.info("GPU detected. Explicitly placing model on GPU.")
                else:
                    logging.warning("No GPU detected. Model will be loaded on CPU.")

                # Load tokenizer and model
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name, torch_dtype=torch.bfloat16
                ).to(device)

                if tokenizer.pad_token is None: 
                    tokenizer.pad_token = tokenizer.eos_token

                # Cache the loaded model and tokenizer
                GLOBAL_HF_MODEL_CACHE[self.model_name] = {
                    'model': model,
                    'tokenizer': tokenizer
                }
                logging.info(f"Model and tokenizer for '{self.model_name}' cached.")
                
                self._model = model
                self._tokenizer = tokenizer

            logging.info(f"Model loaded successfully on device: {self._model.device}")
            
        except Exception as e:
            error_msg = f"Failed to load model '{self.model_name}': {str(e)}"
            logging.error(error_msg)
            logging.error("This could be due to:")
            logging.error("1. Invalid model name or access permissions")
            logging.error("2. Insufficient memory (RAM or GPU VRAM)")
            logging.error("3. Network issues preventing model download")
            raise RuntimeError(error_msg) from e

    @property
    def _llm_type(self) -> str:
        """A required property for custom LangChain LLMs."""
        return "CustomHuggingFaceLLM"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs: Any) -> str:
        """Internal method for LangChain LLM. Handles stateful or stateless generation based on use_kv_cache."""
        if not hasattr(self, '_model') or not hasattr(self, '_tokenizer'):
            raise RuntimeError("Model and tokenizer not initialized. Call _load_model() first.")
            
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)

        if self.model_name == "meta-llama/Llama-3.1-8B-Instruct":
            terminators = [self._tokenizer.eos_token_id, self._tokenizer.convert_tokens_to_ids("<|eot_id|>")]
        else: 
            terminators = [self._tokenizer.eos_token_id]

        try:
            if self.use_kv_cache:
                # Use KV caching for persistent context
                outputs = self._model.generate(
                    **inputs, 
                    max_new_tokens=256, 
                    eos_token_id=terminators,
                    do_sample=True, 
                    temperature=0.6, 
                    top_p=0.9, 
                    use_cache=True,
                    past_key_values=self._past_key_values, 
                    return_dict_in_generate=True
                )
                self._past_key_values = outputs.past_key_values
            else:
                # Stateless generation (no KV cache across calls)
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=256,
                    do_sample=True,
                    temperature=0.6,
                    top_p=0.9,
                    use_cache=False, 
                    return_dict_in_generate=True
                )
            
            response_text = self._tokenizer.decode(
                outputs.sequences[0, inputs['input_ids'].shape[-1]:], 
                skip_special_tokens=True
            )
            return response_text
            
        except Exception as e:
            error_msg = f"Error during text generation: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from e

    
    def reset_kv_cache(self) -> None:
        """Resets the internal KV cache.
        
        This is useful when you want to clear the conversation history
        while keeping the model loaded.
        """
        self._past_key_values = None
        logging.info("KV cache reset for CustomHuggingFaceLLM.")