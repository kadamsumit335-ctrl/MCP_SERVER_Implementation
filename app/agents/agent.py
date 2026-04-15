import os
from typing import Generator
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client with API key from .env
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

def build_prompt(query: str, context: str) -> str:
    """Build a prompt for Gemini using AWS doc context."""
    return f"""You are an expert AWS cloud assistant. Answer the user's question using the AWS 
documentation context provided. Be detailed, clear and helpful. If the context contains relevant information, 
do not say you cannot find information if the context has relevant content.

AWS Documentation Context:
{context[:3000]}

Question: {query}

Provide a clear, detailed answer:"""

def stream_answer(query: str, context: str) -> Generator[str, None, None]:
    """
    Stream Gemini answer token by token using generate_content_stream.
    Yields each token as a string for Streamlit to display progressively.
    """
    prompt = build_prompt(query, context)
    
    try:
        # Use Google Gemini's streaming API
        response = client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=[prompt],
            config={
                "max_output_tokens": 1024,
                "temperature": 0.7,
            }
        )
        
        # Yield each chunk of text as it streams
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"Error: {str(e)}"

def get_answer(query: str, context: str) -> str:
    """Non-streaming version - returns full answer as string."""
    prompt = build_prompt(query, context)
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config={
                "max_output_tokens": 1024,
                "temperature": 0.7,
            }
        )
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"