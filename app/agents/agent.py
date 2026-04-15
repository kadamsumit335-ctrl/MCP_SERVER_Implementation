import os
import torch
from typing import Generator
from threading import Thread
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH =  os.getenv("model_path")

_model = None
_tokenizer = None

def _load_model():
    """Lazy load Gemma 3 model once on first use."""
    global _model, _tokenizer
    
    if _model is not None:
        return _model, _tokenizer

    print("Loading Gemma 3 model... (first time only)")
    
    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH, 
        local_files_only=True
    )
    
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        local_files_only=True,
        torch_dtype=torch.float32,
    )
    
    _model = _model.to("cpu")
    return _model, _tokenizer

def build_prompt(query: str, context: str) -> str:
    """Build a prompt for Gemma 3 using AWS doc context."""
    return f"""<start_of_turn>user
You are an expert AWS cloud assistant. Answer the user's question using the AWS 
documentation context provided. Be detailed, clear and helpful. If the context contains relevant information, 
do not say you cannot find information if the context has relevant content.

AWS Documentation Context:
{context[:3000]}

Question: {query}

Provide a clear, detailed answer:
<end_of_turn>
<start_of_turn>model
"""

def stream_answer(query: str, context: str) -> Generator[str, None, None]:
    """
    Stream Gemma 3 answer token by token.
    Yields each token as a string for Streamlit to display progressively.
    """
    model, tokenizer = _load_model()
    prompt = build_prompt(query, context)
    
    inputs = tokenizer(prompt, return_tensors="pt").to("cpu")
    
    streamer = TextIteratorStreamer(
        tokenizer, skip_prompt=True, skip_special_tokens=True
    )
    
    generation_kwargs = {
        **inputs,
        "streamer": streamer,
        "max_new_tokens": 512,
        "do_sample": False,
    }
    
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()
    
    for token in streamer:
        yield token
        
    thread.join()

def get_answer(query: str, context: str) -> str:
    """Non-streaming version - returns full answer as string."""
    return "".join(stream_answer(query, context))