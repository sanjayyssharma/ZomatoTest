import os

from google import genai
from google.genai import types

from phase2.models import LLMRankingResponse


def call_llm(prompt: str) -> LLMRankingResponse:
    # Use gemini-2.5-flash
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing")
    
    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMRankingResponse,
            temperature=0.1, # Low temperature for more deterministic ranking
        ),
    )
    
    if not response.text:
        raise ValueError("Empty response from LLM")
        
    return LLMRankingResponse.model_validate_json(response.text)
