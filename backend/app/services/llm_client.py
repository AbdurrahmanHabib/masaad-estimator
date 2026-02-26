"""
LLM Client Abstraction
Single entry point for all AI calls in Masaad Estimator.
Primary: Groq LLaMA 3.1 70B (free, 14,400 req/day)
Fallback: Google Gemini 1.5 Flash (free, 15 RPM, 1M tokens/day)
"""
import os
import logging
from typing import Optional
import litellm

logger = logging.getLogger("masaad-api")

GROQ_MODEL = os.getenv("LLM_PRIMARY_MODEL", "groq/llama-3.1-70b-versatile")
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "gemini/gemini-1.5-flash")

# Suppress litellm verbose logging
litellm.set_verbose = False


async def complete(
    messages: list,
    temperature: float = 0.1,
    json_mode: bool = False,
    max_tokens: int = 4096,
) -> str:
    """
    Call primary LLM (Groq). Falls back to Gemini on rate limit or error.
    Returns the response content string.
    """
    kwargs = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    # Try Groq first
    try:
        response = await litellm.acompletion(model=GROQ_MODEL, **kwargs)
        return response.choices[0].message.content
    except litellm.RateLimitError:
        logger.warning("Groq rate limit hit — falling back to Gemini")
    except litellm.AuthenticationError:
        logger.warning("Groq auth error — falling back to Gemini")
    except Exception as e:
        logger.warning(f"Groq error ({type(e).__name__}: {e}) — falling back to Gemini")

    # Fallback to Gemini
    try:
        # Gemini doesn't support json_object response_format the same way
        fallback_kwargs = {k: v for k, v in kwargs.items() if k != "response_format"}
        if json_mode:
            # Prepend instruction to return JSON
            if fallback_kwargs["messages"] and fallback_kwargs["messages"][0]["role"] == "system":
                fallback_kwargs["messages"][0]["content"] += "\n\nIMPORTANT: Respond with valid JSON only."
            else:
                fallback_kwargs["messages"] = [
                    {"role": "system", "content": "You must respond with valid JSON only."}
                ] + fallback_kwargs["messages"]
        response = await litellm.acompletion(model=FALLBACK_MODEL, **fallback_kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Both LLMs failed. Gemini error: {e}")
        raise RuntimeError(f"All LLM providers failed. Last error: {e}")


async def complete_with_vision(
    images_base64: list[str],
    prompt: str,
    temperature: float = 0.1,
    json_mode: bool = False,
) -> str:
    """
    Vision-capable LLM call for scanned PDFs and DWG renderings.
    Uses Groq vision model (llama-3.2-90b-vision-preview) or Gemini fallback.
    images_base64: list of base64-encoded PNG/JPEG strings
    """
    content = []
    for img_b64 in images_base64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
    content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": content}]

    # Try Groq vision model
    groq_vision_model = "groq/llama-3.2-90b-vision-preview"
    try:
        response = await litellm.acompletion(
            model=groq_vision_model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except litellm.RateLimitError:
        logger.warning("Groq vision rate limit — falling back to Gemini vision")
    except Exception as e:
        logger.warning(f"Groq vision error ({e}) — falling back to Gemini vision")

    # Fallback to Gemini (supports vision natively)
    try:
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-flash",
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Both vision LLMs failed: {e}")
        raise RuntimeError(f"Vision LLM failed: {e}")


class LLMClient:
    """
    Class-based wrapper around the module-level complete() / complete_with_vision() functions.
    Used by catalog_pdf_parser, commercial_director, and other services that prefer OOP style.
    """

    async def chat(
        self,
        messages: list,
        temperature: float = 0.1,
        json_mode: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        return await complete(messages, temperature=temperature, json_mode=json_mode, max_tokens=max_tokens)

    async def vision(
        self,
        images_base64: list,
        prompt: str,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> str:
        return await complete_with_vision(images_base64, prompt, temperature=temperature, json_mode=json_mode)

    async def complete(self, messages: list, **kwargs) -> str:
        return await complete(messages, **kwargs)


def get_system_prompt(role: str) -> str:
    """Standard system prompts for different AI roles."""
    prompts = {
        "estimator": (
            "You are a Senior Estimator at Madinat Al Saada Aluminium & Glass Works LLC in Ajman, UAE. "
            "You have 20+ years experience estimating curtain wall, windows, doors, ACP cladding, and all "
            "aluminium & glass facade systems for commercial, residential, and hospitality projects in the UAE and GCC. "
            "You understand UAE building codes, Gulf Extrusions and Elite Aluminium catalogs, LME aluminum pricing, "
            "and the complete estimation workflow from takeoff to commercial quotation. "
            "Always return structured, precise data. When in doubt, flag an RFI rather than guess."
        ),
        "draftsman": (
            "You are a CAD Draftsman at an aluminium & glass company in UAE. "
            "You extract and interpret technical data from architectural DWG/DXF drawings. "
            "You understand layer naming conventions, block insertions, and facade system geometries."
        ),
        "spec_analyst": (
            "You are a Technical Specification Analyst at an aluminium & glass company in UAE. "
            "You read architectural and engineering specifications and extract system requirements, "
            "performance criteria, material specifications, hardware requirements, and project constraints."
        ),
    }
    return prompts.get(role, prompts["estimator"])
