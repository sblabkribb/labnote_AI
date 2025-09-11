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
    version="1.7.0",
    description="Generates structured lab notes using a hybrid RAG + Comprehensive Classification Guide pipeline."
)

# --- [분류 가이드] LLM에게 전체 구조를 알려주기 위한 참고 자료 (v1.7 - 전체 목록 업데이트) ---
CLASSIFICATION_GUIDES = """
[WORKFLOWS]
- WD010: General Design of Experiment
- WD020: Adaptive Laboratory Evolution Design
- WD030: Growth Media Design
- WD040: Parallel Cell Culture/Fermentation Design
- WD050: DNA Oligomer Pool Design
- WD060: Genetic Circuit Design
- WD070: Vector Design
- WD080: Artificial Genome Design
- WD090: Genome Editing Design
- WD100: Protein Library Design
- WD110: De novo Protein/Enzyme Design
- WD120: Retrosynthetic Pathway Design
- WD130: Pathway Library Design
- WB005: Nucleotide Quantification
- WB010: DNA Oligomer Assembly
- WB020: DNA Library Construction
- WB025: Sequencing Library Preparation
- WB030: DNA Assembly
- WB040: DNA Purification
- WB045: DNA Extraction
- WB050: RNA Extraction
- WB060: DNA Multiplexing
- WB070: Cell-free Mixture Preparation
- WB080: Cell-free Protein/Enzyme Expression
- WB090: Protein Purification
- WB100: Growth Media Preparation and Sterilization
- WB110: Competent Cell Construction
- WB120: Biology-mediated DNA Transfers
- WB125: Colony Picking
- WB130: Solid Media Cell Culture
- WB140: Liquid Media Cell Culture
- WB150: PCR-based Target Amplification
- WT010: Nucleotide Sequencing
- WT012: Targeted mRNA Expression Measurement
- WT015: Nucleic Acid Size Verification
- WT020: Protein Expression Measurement
- WT030: Protein/Enzyme Activity Measurement
- WT040: Parallel Cell-free Protein/Enzyme Reaction
- WT045: Mammalian Cell Cytotoxicity Assay
- WT046: Microbial Viability and Cytotoxicity Assay
- WT050: Sample Pretreatment
- WT060: Metabolite Measurement
- WT070: High-throughput Single Metabolite Measurement
- WT080: Image Analysis
- WT085: Mycoplasma Contamination Test
- WT090: High-speed Cell Sorting
- WT100: Micro-scale Parallel Cell Culture
- WT110: Micro-scale Parallel Cell Fermentation
- WT120: Parallel Cell Fermentation
- WT130: Parallel Mammalian Cell Fermentation
- WT140: Lab-scale Fermentation
- WT150: Pilot-scale Fermentation
- WT160: Industrial-scale Fermentation
- WL010: Sequence Variant Analysis
- WL020: Genome Resequencing Analysis
- WL030: De novo Genome Analysis
- WL040: Metagenomic Analysis
- WL050: Transcriptome Analysis
- WL055: Single Cell Analysis
- WL060: Metabolic Pathway Optimization Model Development
- WL070: Phenotypic Data Analysis
- WL080: Protein/Enzyme Optimization Model Development
- WL090: Fermentation Optimization Model Development
- WL100: Foundation Model Development

[UNIT OPERATIONS - HARDWARE (UHW)]
- UHW010: Liquid Handling
- UHW015: Bulk Liquid Dispenser
- UHW020: 96 Channel Liquid Handling
- UHW030: Nanoliter Liquid Dispensing
- UHW040: Desktop Liquid Handling
- UHW050: Single Cell Sequencing Preparation
- UHW060: Colony Picking
- UHW070: Cell Sorting
- UHW080: Cell Lysis
- UHW090: Electroporation
- UHW100: Thermocycling
- UHW110: Real-time PCR
- UHW120: Plate Handling
- UHW130: Sealing
- UHW140: Peeling
- UHW150: Capping Decapping
- UHW160: Sample Storage
- UHW170: Plate Storage
- UHW180: Incubation
- UHW190: HT Aerobic Fermentation
- UHW200: HT Anaerobic Fermentation
- UHW210: Microbioreactor Fermentation
- UHW220: Bioreactor Fermentation
- UHW230: Nucleic Acid Fragment Analysis
- UHW240: Protein Fragment Analysis
- UHW250: Nucleic Acid Purification
- UHW255: Centrifuge
- UHW260: Short-read Sequence Analysis
- UHW265: Sanger Sequencing
- UHW270: Long-read Sequence Analysis
- UHW280: Sequence Quality Control
- UHW290: LC-MS-MS
- UHW300: LC-MS
- UHW310: HPLC
- UHW320: UPLC
- UHW330: GC
- UHW340: GC-MS
- UHW350: GC-MS-MS
- UHW355: SPE-MS-MS
- UHW360: FPLC
- UHW365: Rapid Sugar Analyzer
- UHW370: Oligomer Synthesis
- UHW380: Microplate Reading
- UHW390: Microscopy Imaging
- UHW400: Manual

[UNIT OPERATIONS - SOFTWARE (USW)]
- USW005: Biological Database
- USW010: DNA Oligomer Pool Design
- USW020: Primer Design
- USW030: Vector Design
- USW040: Sequence Optimization
- USW050: Synthesis Screening
- USW060: Structure-based Sequence Generation
- USW070: Protein Structure Prediction
- USW080: Protein Structure Generation
- USW090: Retrosynthetic Pathway Design
- USW100: Enzyme Identification
- USW110: Sequence Alignment
- USW120: Sequence Trimming and Filtering
- USW130: Read Mapping and Alignment
- USW140: Sequence Assembly
- USW145: Metagenomic Assembly
- USW150: Sequence Quality Control
- USW160: Demultiplexing
- USW170: Variant Calling
- USW180: RNA-Seq Analysis
- USW185: Gene Set Enrichment Analysis
- USW190: Proteomics Data Analysis
- USW200: Phylogenetic Analysis
- USW210: Metabolic Flux Analysis
- USW220: Deep Learning Data Preparation
- USW230: Sequence Embedding
- USW240: Deep Learning Model Training
- USW250: Model Evaluation
- USW260: Hyperparameter Tuning
- USW270: Model Deployment
- USW280: Monitoring and Reporting
- USW290: Phenotype Data Preprocessing
- USW300: XCMS Analysis
- USW310: Flow Cytometry Analysis
- USW320: DNA Assembly Simulation
- USW325: Gene Editing Simulation
- USW330: Well Plate Mapping
- USW340: Computation
"""

# Pydantic 모델
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None

# --- 연구노트 생성 API ---
@app.post("/generate_labnote", response_model=QueryResponse)
async def generate_labnote(request: QueryRequest):
    """
    Generates a structured lab note based on a user query by retrieving context
    from SOPs and using a highly structured prompt with classification guides.
    """
    try:
        logger.info(f"Received lab note query: '{request.query}'")

        # 1. 컨텍스트 검색
        retrieved_docs = rag_pipeline.retrieve_context(request.query)
        formatted_context = rag_pipeline.format_context_for_prompt(retrieved_docs)
        sources = list(set([doc.metadata.get('source', 'Unknown').split('/')[-1] for doc in retrieved_docs]))

        # 2. **강화된 프롬프트 엔지니어링 (v1.7 - 전체 가이드 적용)**
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        prompt = f"""You are a meticulous AI Principal Scientist. Your primary goal is accuracy and relevance.

[TASK]
Generate a formal lab note in Markdown. Use the [CONTEXT] as the primary source for content, and the [CLASSIFICATION GUIDES] to ensure correct naming and structure.

[CONTEXT]
{formatted_context}

[USER QUERY]
{request.query}

[CLASSIFICATION GUIDES]
{CLASSIFICATION_GUIDES}

---
[CRITICAL RULES]
1.  **Content Source:** You MUST base the detailed content (Input, Reagent, Method, etc.) on the [CONTEXT]. Use the [CLASSIFICATION GUIDES] mainly to identify the correct Workflow/Unit Operation IDs and names.
2.  **Context Validation (Guardrail):** If the [CONTEXT] is clearly irrelevant to the [USER QUERY], you MUST respond ONLY with: "Information not available in the provided SOPs for the query: '{request.query}'". Do not use the guides to invent a protocol.
3.  **Handling Ambiguity:** If the user's query is general, use both the [CONTEXT] and [CLASSIFICATION GUIDES] to select the most appropriate protocol to write about. Do not leave the "Relevant Unit Operations" section empty unless no context was found.
4.  **Completeness:** You must extract the *complete* Unit Operation sections from the [CONTEXT], including all fields.
---

[OUTPUT TEMPLATE]
---
title: "[AI Generated] {request.query}"
experimenter: AI Assistant
created_date: '{current_date}'
---

## Workflow: [Create a concise, relevant title using the Guides and Context]

> [Write a 1-2 sentence summary of this workflow based on the context]

## 🗂️ Relevant Unit Operations
> <!-- UNITOPERATION_LIST_START -->

[Extract and list the complete, relevant Unit Operation sections from the context here.]

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
        
        if generated_text.startswith("```markdown"):
            generated_text = generated_text.lstrip("```markdown").rstrip("```").strip()
        
        logger.info("Successfully received and processed response from Ollama.")

        return QueryResponse(response=generated_text, sources=sources)

    except Exception as e:
        logger.error(f"Error during lab note generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

# --- 일반 대화 API ---
@app.post("/chat", response_model=QueryResponse)
async def general_chat(request: QueryRequest):
    """
    Handles general, conversational queries with the LLM without RAG.
    """
    try:
        logger.info(f"Received general chat query: '{request.query}'")

        prompt = f"""You are a helpful AI assistant specializing in biology and life sciences. Answer the following question clearly and concisely.

Question: {request.query}"""

        logger.info("Sending general request to Ollama model...")
        llm_model_name = os.getenv("LLM_MODEL", "biomistral")
        ollama_response = ollama.chat(
            model=llm_model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.7}
        )
        generated_text = ollama_response['message']['content'].strip()
        logger.info("Successfully received and processed general response from Ollama.")

        return QueryResponse(response=generated_text, sources=None)

    except Exception as e:
        logger.error(f"Error during general chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")


@app.get("/", summary="Health Check")
def health_check():
    """Check if the API server is running."""
    return {"status": "ok"}

