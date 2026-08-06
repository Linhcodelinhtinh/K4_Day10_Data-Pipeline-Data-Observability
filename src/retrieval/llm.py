from __future__ import annotations

from core.config import Settings, normalized_provider, require_llm_credentials


def build_llm(
    settings: Settings,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout_seconds: float = 60.0,
):
    if max_tokens < 1:
        raise ValueError("max_tokens must be at least 1.")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    provider = normalized_provider(settings)
    require_llm_credentials(settings)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            api_key=settings.google_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=timeout_seconds,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            timeout=timeout_seconds,
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model_name=settings.model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens_to_sample=max_tokens,
            timeout=timeout_seconds,
        )
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            timeout=timeout_seconds,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            num_predict=max_tokens,
            client_kwargs={"timeout": timeout_seconds},
        )
    if provider == "custom":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.custom_llm_api_key or "unused",
            base_url=settings.custom_llm_base_url,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            timeout=timeout_seconds,
        )
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict) and item.get("text"):
                chunks.append(str(item["text"]))
        return "\n".join(chunks).strip()
    return str(content or "")


def generate(
    settings: Settings,
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout_seconds: float = 60.0,
) -> str:
    """Generate text through the configured provider without exposing credentials."""
    if not prompt.strip():
        raise ValueError("prompt must not be empty.")

    from langchain_core.messages import HumanMessage, SystemMessage

    provider = normalized_provider(settings)
    messages = []
    if system_prompt and system_prompt.strip():
        messages.append(SystemMessage(content=system_prompt.strip()))
    messages.append(HumanMessage(content=prompt.strip()))

    try:
        llm = build_llm(
            settings,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        response = llm.invoke(messages)
    except Exception as exc:
        raise RuntimeError(
            f"LLM request failed for provider={provider}: {type(exc).__name__}: {exc}"
        ) from exc
    return _content_to_text(getattr(response, "content", response))
