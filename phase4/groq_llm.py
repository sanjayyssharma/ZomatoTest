import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from phase2.models import LLMRankingResponse

def call_groq_llm(prompt: str) -> LLMRankingResponse:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing")
        
    client = Groq(api_key=api_key)
    
    # Use llama-3.1-8b-instant for fast, cheap inference suitable for JSON ranking
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a JSON-only API. You must output exactly the JSON format requested, without any markdown formatting or extra text."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from Groq LLM")
        
    print("\n--- RAW LLM OUTPUT ---")
    print(content)
    print("----------------------\n")
        
    return LLMRankingResponse.model_validate_json(content)
