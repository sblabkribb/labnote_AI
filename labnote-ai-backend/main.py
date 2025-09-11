import os
import logging
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import ollama
from dotenv import load_dotenv

# **개선점**: RAG 파이프라인 싱글턴 인스턴스를 임포트합니다.
from rag_pipeline import rag_pipeline

# .env 파일 로드 및 로깅 설정
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="LabNote AI Assistant Backend",
    version="1.2.0",
    description="Generates structured lab notes using BioMistral and a RAG pipeline."
)

# Pydantic 모델
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None

# API 엔드포인트
@app.post("/generate_labnote", response_model=QueryResponse)
async def generate_labnote(request: QueryRequest):
    """
    Generates a structured lab note based on a user query by retrieving context
    from SOPs and using a highly structured prompt.
    """
    try:
        logger.info(f"Received query: '{request.query}'")

        # 1. 컨텍스트 검색
        retrieved_docs = rag_pipeline.retrieve_context(request.query)
        formatted_context = rag_pipeline.format_context_for_prompt(retrieved_docs)
        sources = list(set([doc.metadata.get('source', 'Unknown').split('/')[-1] for doc in retrieved_docs]))

        # 2. **강화된 프롬프트 엔지니어링**
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        prompt = f"""You are a meticulous AI Principal Scientist. Your task is to generate a formal lab note in Markdown, strictly following the template below. Use only the provided context. If the context is insufficient, state "Information not available in the provided SOPs."

[CONTEXT]
{formatted_context}

[USER QUERY]
{request.query}

[OUTPUT TEMPLATE]
---
title: "[AI Generated] {request.query}"
experimenter: AI Assistant
created_date: '{current_date}'
---

## Workflow: [Create a concise title based on the user query]

> A one-sentence summary of this workflow.

## 🗂️ Relevant Unit Operations
> <!-- UNITOPERATION_LIST_START -->

[Extract and list the complete, relevant Unit Operation sections from the context here. Each section must include all its original fields like Description, Meta, Input, Reagent, Method, Output, etc.]

> <!-- UNITOPERATION_LIST_END -->
"""

        # 3. Ollama API 호출
        logger.info("Sending request to Ollama model...")
        llm_model_name = os.getenv("LLM_MODEL", "biomistral")
        ollama_response = ollama.chat(
            model=llm_model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.05}
        )
        generated_text = ollama_response['message']['content'].strip()
        logger.info("Successfully received and processed response from Ollama.")

        return QueryResponse(response=generated_text, sources=sources)

    except Exception as e:
        logger.error(f"Error during lab note generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

@app.get("/", summary="Health Check")
def health_check():
    """Check if the API server is running."""
    return {"status": "ok"}
