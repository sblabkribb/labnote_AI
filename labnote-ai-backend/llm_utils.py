import os
import re
import logging
import ollama
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

async def call_llm_api(system_prompt: str, user_prompt: str, model_name: str = None):
    """LLM API를 호출하는 범용 비동기 함수."""
    if model_name is None:
        model_name = os.getenv("LLM_MODEL", "biollama3")

    logger.info(f"Calling LLM: {model_name} for a specific task.")
    try:
        # OLLAMA_BASE_URL 환경 변수를 사용하여 클라이언트 호스트를 명시적으로 설정합니다.
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        client = ollama.AsyncClient(host=ollama_base_url)

        response = await client.chat(
            model=model_name,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            options={'temperature': 0.1, 'top_p': 0.8}
        )
        content = response['message']['content'].strip()
        # 후처리: 불필요한 마크다운 코드 블록 제거
        if content.startswith("```") and "```" in content[3:]:
            content = re.sub(r'^```[a-zA-Z]*\\n', '', content)
            content = re.sub(r'\\n```$', '', content)
        return content
    except Exception as e:
        logger.error(f"LLM API call failed: {e}", exc_info=True)
        return f"(LLM Error: Could not generate content due to: {e})"
