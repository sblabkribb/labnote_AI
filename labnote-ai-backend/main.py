import os
import logging
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import ollama
from dotenv import load_dotenv

# RAG 파이프라인 싱글턴 인스턴스를 임포트합니다.
from rag_pipeline import rag_pipeline

# .env 파일 로드 및 로깅 설정
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="LabNote AI Assistant Backend",
    version="1.5.0",
    description="Generates structured lab notes (RAG) and provides general chat functionality."
)

# Pydantic 모델
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None

# --- [기존 기능] 연구노트 생성 API ---
@app.post("/generate_labnote", response_model=QueryResponse)
async def generate_labnote(request: QueryRequest):
    """
    Generates a structured lab note based on a user query by retrieving context
    from SOPs and using a highly structured prompt.
    """
    try:
        logger.info(f"Received lab note query: '{request.query}'")

        # 1. 컨텍스트 검색
        retrieved_docs = rag_pipeline.retrieve_context(request.query)
        formatted_context = rag_pipeline.format_context_for_prompt(retrieved_docs)
        sources = list(set([doc.metadata.get('source', 'Unknown').split('/')[-1] for doc in retrieved_docs]))

        # 2. **강화된 프롬프트 엔지니어링 (v1.4 - Guardrail 적용)**
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        prompt = f"""You are a meticulous AI Principal Scientist. Your primary goal is accuracy and relevance.

[TASK]
Generate a formal lab note in Markdown based on the [USER QUERY]. You MUST strictly follow the [OUTPUT TEMPLATE] and use ONLY the provided [CONTEXT].

[CONTEXT]
{formatted_context}

[USER QUERY]
{request.query}

---
[CRITICAL RULES]
1.  **Context Validation (Guardrail):** Before writing, you MUST verify if the [CONTEXT] is relevant to the [USER QUERY].
    -   **If RELEVANT:** Proceed with generation based on the template.
    -   **If IRRELEVANT or INSUFFICIENT:** Do NOT generate a lab note. Instead, respond ONLY with the message: "Information not available in the provided SOPs for the query: '{request.query}'"
2.  **Handling Ambiguity:** If the user's query is general (e.g., "make a lab note"), use your best judgment to select the most central and complete protocol from the [CONTEXT] to feature in the "Relevant Unit Operations" section. Do not leave the section empty unless no context was found at all.
3.  **Completeness:** You must extract the *complete* Unit Operation sections, including all fields (Description, Meta, Input, Reagent, Method, Output, etc.). Do not summarize or omit fields.
---

[OUTPUT TEMPLATE]
---
title: "[AI Generated] {request.query}"
experimenter: AI Assistant
created_date: '{current_date}'
---

## Workflow: [Create a concise, relevant title based on the user query and context]

> [Write a 1-2 sentence summary of this workflow based on the context]

## 🗂️ Relevant Unit Operations
> <!-- UNITOPERATION_LIST_START -->

[Based on the rules above, extract and list the complete, relevant Unit Operation sections from the context here.]

> <!-- UNITOPERATION_LIST_END -->
"""

        # 3. Ollama API 호출
        logger.info("Sending request to Ollama model for lab note generation...")
        llm_model_name = os.getenv("LLM_MODEL", "biomistral")
        ollama_response = ollama.chat(
            model=llm_model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.05}
        )
        generated_text = ollama_response['message']['content'].strip()
        
        # 후처리: 가끔 모델이 markdown 코드 블록을 추가하는 경우 제거
        if generated_text.startswith("```markdown"):
            generated_text = generated_text.lstrip("```markdown").rstrip("```").strip()
        
        logger.info("Successfully received and processed response from Ollama.")

        return QueryResponse(response=generated_text, sources=sources)

    except Exception as e:
        logger.error(f"Error during lab note generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

# --- [새로운 기능] 일반 대화 API ---
@app.post("/chat", response_model=QueryResponse)
async def general_chat(request: QueryRequest):
    """
    Handles general, conversational queries with the LLM without RAG.
    """
    try:
        logger.info(f"Received general chat query: '{request.query}'")

        # 1. RAG 없이 간단하고 직접적인 프롬프트 구성
        prompt = f"""You are a helpful AI assistant specializing in biology and life sciences. Answer the following question clearly and concisely.

Question: {request.query}"""

        # 2. Ollama API 호출
        logger.info("Sending general request to Ollama model...")
        llm_model_name = os.getenv("LLM_MODEL", "biomistral")
        ollama_response = ollama.chat(
            model=llm_model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.7} # 일반 대화를 위해 창의성을 약간 높임
        )
        generated_text = ollama_response['message']['content'].strip()
        logger.info("Successfully received and processed general response from Ollama.")

        # 일반 대화에서는 참고 자료(sources)가 없으므로 None으로 반환
        return QueryResponse(response=generated_text, sources=None)

    except Exception as e:
        logger.error(f"Error during general chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")


@app.get("/", summary="Health Check")
def health_check():
    """Check if the API server is running."""
    return {"status": "ok"}