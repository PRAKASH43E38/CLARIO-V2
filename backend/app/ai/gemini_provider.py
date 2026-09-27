from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from backend.app.ai.base import BaseAIProvider
import json

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider for CLARIO."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if not GENAI_AVAILABLE:
            raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generates a structured machine-readable result conforming to response_model."""
        
        # Build the full prompt with schema instructions
        schema = response_model.model_json_schema()
        
        full_prompt = f"""
{system_instruction or ''}

{prompt}

Return ONLY valid JSON matching this exact schema:
{json.dumps(schema, indent=2)}

Do not include any markdown formatting, explanations, or additional text. Just the JSON object.
"""
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )
        
        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )
        
        # Parse the JSON response
        try:
            response_text = response.text.strip()
            # Handle potential markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            data = json.loads(response_text)
            return response_model(**data)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Failed to parse structured response from Gemini: {e}\nResponse: {response.text}")

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generates a raw text response."""
        
        full_prompt = f"{system_instruction or ''}\n\n{prompt}"
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
        )
        
        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )
        
        return response.text.strip()