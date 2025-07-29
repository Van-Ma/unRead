"""Test script for verifying global app functionality."""

import sys
import os
import logging
from typing import Dict, Any

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from python.models.langchain import get_global_app, set_global_app
from python.models.model_parameters import ModelParameters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_app_initialization():
    """Test that the global app initializes correctly."""
    print("\n=== Testing app initialization ===")
    app = get_global_app()
    assert app is not None, "Failed to initialize global app"
    print("✓ Global app initialized successfully")

def test_app_switching():
    """Test switching between Base and RAG models."""
    print("\n=== Testing model switching ===")
    
    # Test Base model
    base_params = {
        "framework_type": "LangChain",
        "backend": "HuggingFace",
        "model_version": "Base",
        "hf_params": {
            "model_name": "meta-llama/Llama-3.1-8B-Instruct",
            "use_kv_cache": True
        }
    }
    
    set_global_app(base_params)
    base_app = get_global_app()
    assert base_app is not None, "Failed to set Base model"
    print("✓ Base model set successfully")
    
    # Test RAG model
    rag_params = {
        "framework_type": "LangChain",
        "backend": "HuggingFace",
        "model_version": "RAG",
        "hf_params": {
            "model_name": "meta-llama/Llama-3.1-8B-Instruct",
            "use_kv_cache": True
        }
    }
    
    set_global_app(rag_params)
    rag_app = get_global_app()
    assert rag_app is not None, "Failed to set RAG model"
    print("✓ RAG model set successfully")

def test_chat_workflow():
    """Test basic chat workflow with the global app."""
    print("\n=== Testing chat workflow ===")
    
    # Set up test parameters
    test_params = {
        "framework_type": "LangChain",
        "backend": "HuggingFace",
        "model_version": "Base",
        "hf_params": {
            "model_name": "meta-llama/Llama-3.1-8B-Instruct",
            "use_kv_cache": True
        }
    }
    
    set_global_app(test_params)
    app = get_global_app()
    
    # Test chat interaction
    thread_id = "test_thread_123"
    user_message = "Hello, how are you?"
    
    try:
        # Invoke the app with a test message
        result = app.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            {"configurable": {"thread_id": thread_id}}
        )
        
        assert result is not None, "No response from app"
        assert "messages" in result, "Response missing 'messages' key"
        
        print(f"✓ Chat interaction successful. Response: {result['messages'][-1]['content'][:100]}...")
        
    except Exception as e:
        print(f"✗ Chat interaction failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("\n=== Starting Global App Tests ===")
    
    try:
        test_app_initialization()
        test_app_switching()
        test_chat_workflow()
        
        print("\n=== All tests passed successfully! ===")
    except Exception as e:
        print(f"\n!!! Test failed: {str(e)}")
        sys.exit(1)
