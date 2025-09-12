import os
import logging
import datetime
import uuid
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from collections import Counter
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
    version="5.0.0", # Interactive 2-Step Generation
    description="Generates lab notes by first recommending a structure (WF/UOs) and then filling the user-confirmed structure."
)

# --- 인메모리 대화 기록 저장소 ---
conversation_histories: Dict[str, List[Dict[str, str]]] = {}

# --- Pydantic 모델 정의 ---
class QueryRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None

class StructureResponse(BaseModel):
    recommended_workflow_id: str
    recommended_unit_operation_ids: List[str]
    sources: List[str]

class CreateNoteRequest(BaseModel):
    query: str
    workflow_id: str
    unit_operation_ids: List[str]
    experimenter: Optional[str] = "AI Assistant"

class LabNoteResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

# --- 워크플로우 및 단위 작업 가이드 (상수) ---
# (WORKFLOW_GUIDE_DATA와 UNIT_OPERATION_GUIDE_DATA는 매우 길기 때문에 생략합니다. 기존 코드를 그대로 사용하시면 됩니다.)
WORKFLOW_GUIDE_DATA = """
# Workflows Guide
## Design (설계)
- WD010: General Design of Experiment (실험설계법(DOE)을 활용한 범용적 실험 조건 최적화)
- WD020: Adaptive Laboratory Evolution Design (무작위 돌연변이 및 인공 진화를 통한 하향식 설계)
- WD030: Growth Media Design (데이터 기반 실험 설계를 통한 균주 배양용 성장 배지 최적화)
- WD040: Parallel Cell Culture/Fermentation Design (단백질, 효소 대량 배양 또는 균주 활성 테스트 조건 설계)
- WD050: DNA Oligomer Pool Design (목표 DNA 서열 조립을 위한 올리고머 풀 설계)
- WD060: Genetic Circuit Design (바이오센서, 논리 게이트 등 특정 목적의 유전 회로 설계)
- WD070: Vector Design (플라스미드, BAC, YAC 등 벡터 형태의 DNA 구축 설계)
- WD080: Artificial Genome Design (유전체 압축, 코돈 재설계 등 새로운 유전체 디자인)
- WD090: Genome Editing Design (CRISPR 기반 유전체 편집을 위한 gRNA 설계)
- WD100: Protein Library Design (단백질 활성, 특이성, 발현 최적화를 위한 라이브러리 설계)
- WD110: De novo Protein/Enzyme Design (딥러닝 도구를 이용한 새로운 단백질 또는 효소 설계)
- WD120: Retrosynthetic Pathway Design (역합성 분석을 통한 목표 대사산물 생산 경로 설계)
- WD130: Pathway Library Design (대사 경로 기능 최적화를 위한 DNA 부품 라이브러리 설계)
## Build (구축)
- WB005: Nucleotide Quantification (UV 흡광도 및 형광 분석을 통한 핵산 정량 및 순도 평가)
- WB010: DNA Oligomer Assembly (DNA 올리고머 풀로부터 정확한 DNA 서열 조립)
- WB020: DNA Library Construction (DNA 돌연변이, 메타게놈, 경로 라이브러리 제작)
- WB025: Sequencing Library Preparation (차세대 시퀀싱(NGS)을 위한 DNA/RNA 라이브러리 준비)
- WB030: DNA Assembly (여러 DNA 단편을 특정 순서로 조립하여 유전 구조물 제작)
- WB040: DNA Purification (컬럼, 비드 등을 이용해 조 DNA 추출물에서 고순도 DNA 정제)
- WB045: DNA Extraction (세포 용해를 통해 생물학적 샘플로부터 DNA 추출)
- WB050: RNA Extraction (유전자 발현 분석 등을 위해 생물학적 샘플에서 RNA 분리)
- WB060: DNA Multiplexing (식별을 위해 세포에 바코드를 할당하고 NGS용 DNA 풀링)
- WB070: Cell-free Mixture Preparation (무세포 반응을 위한 마스터 용액 및 세포 추출물 준비)
- WB080: Cell-free Protein/Enzyme Expression (무세포 반응 시스템에서 목표 단백질 또는 효소 생산)
- WB090: Protein Purification (자동화 장비를 이용한 고처리량, 고순도 단백질 정제)
- WB100: Growth Media Preparation and Sterilization (설계된 고체 및 액체 배지의 대량 생산, 멸균 및 보관)
- WB110: Competent Cell Construction (형질전환을 위한 고효율의 Competent cell 제작)
- WB120: Biology-mediated DNA Transfers (설계된 벡터 플라스미드를 세포 내로 자동 형질전환)
- WB125: Colony Picking (자동화 콜로니 피커를 이용한 단일 콜로니 분리 및 배양)
- WB130: Solid Media Cell Culture (고체 배지에서의 세포 배양, 스크리닝 및 단일 콜로니 분리)
- WB140: Liquid Media Cell Culture (액체 배지에서의 접종 및 회분 배양 프로세스)
- WB150: PCR-based Target Amplification (PCR을 이용해 복잡한 템플릿에서 특정 유전자 서열 증폭)
## Test (시험)
- WT010: Nucleotide Sequencing (NGS 또는 Sanger 시퀀싱을 이용한 염기서열 데이터 생성)
- WT012: Targeted mRNA Expression Measurement (RT-qPCR, ddPCR 등을 이용한 특정 전사체 수준 측정)
- WT015: Nucleic Acid Size Verification (전기영동을 이용한 DNA/RNA 단편 크기 및 무결성 확인)
- WT020: Protein Expression Measurement (겔 전기영동, LC-MS 등을 통한 목표 단백질 발현 수준 정량화)
- WT030: Protein/Enzyme Activity Measurement (정제된 단백질 또는 효소의 활성을 특정 방법으로 측정)
- WT040: Parallel Cell-free Protein/Enzyme Reaction (무세포 시스템에서 단백질 발현과 활성을 동시에 측정)
- WT045: Mammalian Cell Cytotoxicity Assay (포유류/진핵 세포의 생존력 및 세포 독성 효과 정량화)
- WT046: Microbial Viability and Cytotoxicity Assay (미생물 세포의 성장 억제 및 생존력 측정 (MIC/MBC 등))
- WT050: Sample Pretreatment (배양액에서 대사체 분리 및 분석을 위한 전처리)
- WT060: Metabolite Measurement (GC-MS, LC-MS 등을 이용한 대사체 정량 분석)
- WT070: High-throughput Single Metabolite Measurement (바이오센서 등을 이용한 단일 유형 대사산물 고속 측정)
- WT080: Image Analysis (고속 광학 장치를 이용한 세포 성장, 형태, 위치 분석)
- WT085: Mycoplasma Contamination Test (포유류 세포 배양의 마이코플라즈마 오염 스크리닝)
- WT090: High-speed Cell Sorting (유전 회로 신호를 기반으로 특정 세포 집단 고속 분리)
- WT100: Micro-scale Parallel Cell Culture (96-딥웰 플레이트에서의 마이크로 스케일 병렬 세포 배양)
- WT110: Micro-scale Parallel Cell Fermentation (OD, pH, 온도, DO 모니터링을 통한 마이크로 스케일 발효)
- WT120: Parallel Cell Fermentation (15-250ml 규모의 실시간 모니터링 병렬 세포 발효)
- WT130: Parallel Mammalian Cell Fermentation (단백질 생산 극대화를 위한 동물 세포 병렬 발효)
- WT140: Lab-scale Fermentation (10L 미만 규모의 실험실 스케일 발효 공정 개발)
- WT150: Pilot-scale Fermentation (10L-500L 규모의 파일럿 스케일 발효 공정)
- WT160: Industrial-scale Fermentation (500L 이상 산업 스케일의 대규모 발효 공정)
## Learn (학습)
- WL010: Sequence Variant Analysis (유전자, 플라스미드 등 주형 DNA 서열의 변이 비교 분석)
- WL020: Genome Resequencing Analysis (참조 유전체가 있는 생물체의 SNP 등 유전체 변이 분석)
- WL030: De novo Genome Analysis (참조 유전체가 없는 신규 생물체의 유전체 조립 및 분석)
- WL040: Metagenomic Analysis (대용량 메타게놈 서열 데이터의 유전자 및 균주 식별, 기능 예측)
- WL050: Transcriptome Analysis (다양한 조건 하의 전사체(mRNA) 데이터 및 유전자 발현 차이 분석)
- WL055: Single Cell Analysis (단일 세포 RNA 시퀀싱 등을 통한 세포 이질성 및 기능 분석)
- WL060: Metabolic Pathway Optimization Model Development (측정된 대사체 데이터 분석 및 대사 경로 최적화 모델 개발)
- WL070: Phenotypic Data Analysis (표현형 데이터 처리 및 분석을 통한 유전형-표현형 관계 규명)
- WL080: Protein/Enzyme Optimization Model Development (단백질/효소의 특성(활성, 용해도 등) 최적화 모델 개발)
- WL090: Fermentation Optimization Model Development (발효 데이터를 기반으로 목표 화합물 생산 최적 조건 탐색)
- WL100: Foundation Model Development (대규모 서열 데이터셋을 이용한 파운데이션 모델 훈련)
"""
UNIT_OPERATION_GUIDE_DATA = """
# Unit Operations Guide
## Hardware (UHW)
- UHW010: Liquid Handling (액체 시약의 정밀 분주, 희석, 혼합 등 기본 작업)
- UHW015: Bulk Liquid Dispenser (배지, 버퍼 등 대용량 액체의 빠른 분배)
- UHW020: 96 Channel Liquid Handling (96-웰 플랫폼에서의 고처리량 동시 액체 분주/전송)
- UHW030: Nanoliter Liquid Dispensing (나노리터 단위의 초미세 액체 정밀 분주)
- UHW040: Desktop Liquid Handling (소규모 자동화 실험을 위한 소형 액체 핸들링 시스템)
- UHW050: Single Cell Sequencing Preparation (단일 세포 분석을 위한 세포 캡슐화 및 라이브러리 준비)
- UHW060: Colony Picking (한천 배지에서 단일 콜로니를 분리하여 액체 배양)
- UHW070: Cell Sorting (세포의 생물학적 특성에 따른 고속 세포 분류 및 선택)
- UHW080: Cell Lysis (세포를 파괴하여 내부 구성물(DNA, 단백질 등) 추출)
- UHW090: Electroporation (전기장을 이용해 세포 내로 DNA, RNA 등 외부 분자 도입)
- UHW100: Thermocycling (PCR 등 반응 촉진을 위한 반복적인 온도 순환)
- UHW110: Real-time PCR (특정 DNA/RNA 서열의 증폭 및 실시간 정량 분석)
- UHW120: Plate Handling (로봇 팔을 이용한 자동화 장비 간 플레이트 이동)
- UHW130: Sealing (PCR, 배양, 보관 시 샘플 무결성을 위한 플레이트 밀봉)
- UHW140: Peeling (자동화 공정을 위한 플레이트 덮개 제거)
- UHW150: Capping Decapping (샘플 튜브 캡의 자동 개폐)
- UHW160: Sample Storage (자동화된 DNA 또는 세포 샘플 저장 및 검색 시스템)
- UHW170: Plate Storage (고처리량 실험을 위한 자동화 플레이트 저장 및 검색)
- UHW180: Incubation (세포 성장 및 반응을 위한 특정 조건 유지 (온도, 습도 등))
- UHW190: HT Aerobic Fermentation (산소 조건에서의 고처리량 병렬 미생물/세포 배양)
- UHW200: HT Anaerobic Fermentation (무산소 조건에서의 고처리량 병렬 미생물/세포 배양)
- UHW210: Microbioreactor Fermentation (고급 모니터링 기능의 마이크로 규모 생물반응기 배양)
- UHW220: Bioreactor Fermentation (리터 규모 생물반응기에서의 세포 배양 (회분, 유가, 연속))
- UHW230: Nucleic Acid Fragment Analysis (크기 기반 핵산 단편 분리, 식별 및 특성 분석)
- UHW240: Protein Fragment Analysis (단백질 단편의 구조, 크기, 변형, 상호작용 연구)
- UHW250: Nucleic Acid Purification (자동화 장치를 이용한 고순도 DNA/RNA 정제)
- UHW255: Centrifuge (원심력을 이용한 샘플 내 밀도 별 성분 분리)
- UHW260: Short-read Sequence Analysis (NGS 기술을 이용한 짧은 서열 기반 시퀀싱)
- UHW265: Sanger Sequencing (표적 유전자/플라스미드 검증을 위한 전통적 시퀀싱)
- UHW270: Long-read Sequence Analysis (복잡한 유전체 영역 분석을 위한 긴 서열 기반 시퀀싱)
- UHW280: Sequence Quality Control (단일 세포 분석을 위한 시퀀싱 데이터 품질 평가)
- UHW290: LC-MS-MS (탠덤 질량분석기가 결합된 고성능 액체 크로마토그래피)
- UHW300: LC-MS (질량분석기가 결합된 액체 크로마토그래피)
- UHW310: HPLC (고성능 액체 크로마토그래피)
- UHW320: UPLC (초고성능 액체 크로마토그래피)
- UHW330: GC (가스 크로마토그래피)
- UHW340: GC-MS (질량분석기가 결합된 가스 크로마토그래피)
- UHW350: GC-MS-MS (탠덤 질량분석기가 결합된 가스 크로마토그래피)
- UHW355: SPE-MS-MS (고체상 추출 및 탠덤 질량 분석)
- UHW360: FPLC (단백질 등 생체 분자 정제에 최적화된 고속 단백질 액체 크로마토그래피)
- UHW365: Rapid Sugar Analyzer (효소 기반 센서를 이용한 특정 당(포도당 등)의 신속 정량)
- UHW370: Oligomer Synthesis (화학적 방법을 이용한 맞춤형 DNA/RNA 올리고머 병렬 합성)
- UHW380: Microplate Reading (형광, OD 등을 측정하여 단백질/세포 활성 정량화)
- UHW390: Microscopy Imaging (동물 세포 등 생물학적 샘플의 현미경 이미지 촬영)
- UHW400: Manual (시약 준비, 실험기구 준비 등 수동으로 진행되는 모든 실험 과정)
## Software (USW)
- USW005: Biological Database (표준 생물학적 부품 데이터베이스 검색 및 선택)
- USW010: DNA Oligomer Pool Design (효율적인 DNA 조립을 위한 올리고머 풀 설계)
- USW020: Primer Design (PCR, 돌연변이 생성 등을 위한 프라이머 설계)
- USW030: Vector Design (삽입 서열과 플라스미드 백본을 고려한 벡터 맵 설계)
- USW040: Sequence Optimization (특정 숙주에서 단백질 발현을 극대화하기 위한 코돈 최적화)
- USW050: Synthesis Screening (생물 보안을 위한 잠재적 위험 DNA 서열 스크리닝)
- USW060: Structure-based Sequence Generation (AI 모델을 이용한 단백질 구조 기반 서열 생성)
- USW070: Protein Structure Prediction (AI 모델을 이용한 단백질 3차 구조 예측)
- USW080: Protein Structure Generation (AI 모델을 이용한 새로운 기능의 단백질 구조 생성)
- USW090: Retrosynthetic Pathway Design (역합성 분석을 통한 생합성 경로 예측 및 신규 경로 발견)
- USW100: Enzyme Identification (데이터베이스 검색 또는 예측을 통한 경로 내 적합 효소 탐색)
- USW110: Sequence Alignment (서열 유사성 비교 및 상동 서열 식별)
- USW120: Sequence Trimming and Filtering (데이터 품질 향상을 위한 저품질 시퀀싱 리드 제거)
- USW130: Read Mapping and Alignment (시퀀싱 리드를 참조 서열에 매핑 및 정렬)
- USW140: Sequence Assembly (시퀀싱 리드를 조립하여 전체 유전자, 경로, 염색체 재구성)
- USW145: Metagenomic Assembly (복잡한 미생물 군집으로부터 유전체 재구성)
- USW150: Sequence Quality Control (FastQ, Fast5 등 시퀀싱 파일 품질 관리(QC))
- USW160: Demultiplexing (바코드 기반으로 NGS 리드를 개별 샘플로 분리)
- USW170: Variant Calling (리드 매핑 기반의 SNP, indel 등 변이 탐지)
- USW180: RNA-Seq Analysis (전사체 데이터 처리 및 유전자 발현 정량화 분석)
- USW185: Gene Set Enrichment Analysis (유전자 발현 데이터에서 유의미한 생물학적 경로 분석)
- USW190: Proteomics Data Analysis (질량 분석 데이터 처리 및 단백질 식별/정량 분석)
- USW200: Phylogenetic Analysis (서열 유사성에 기반한 계통 발생 관계 분석)
- USW210: Metabolic Flux Analysis (세포 대사 및 경로 최적화를 위한 대사 흐름 모델링/분석)
- USW220: Deep Learning Data Preparation (AI 모델 훈련 및 평가를 위한 데이터셋 준비 및 배치화)
- USW230: Sequence Embedding (생물학적 서열을 기계 학습용 수치 표현으로 변환)
- USW240: Deep Learning Model Training (훈련 데이터를 이용한 딥러닝 모델 훈련 절차)
- USW250: Model Evaluation (정확도, 정밀도 등 평가지표를 이용한 모델 성능 평가)
- USW260: Hyperparameter Tuning (베이즈 최적화 등을 이용한 모델 하이퍼파라미터 튜닝)
- USW270: Model Deployment (훈련된 모델을 서비스로 배포)
- USW280: Monitoring and Reporting (배포된 AI 모델의 성능 및 자원 사용량 모니터링)
- USW290: Phenotype Data Preprocessing (측정된 표현형 데이터의 정제, 구성, 변환 등 전처리)
- USW300: XCMS Analysis (크로마토그래피 및 질량분석 데이터 분석 및 시각화)
- USW310: Flow Cytometry Analysis (유세포 분석 데이터 분석 및 시각화)
- USW320: DNA Assembly Simulation (Golden Gate, Gibson 등 DNA 조립 성공률 향상을 위한 시뮬레이션)
- USW325: Gene Editing Simulation (CRISPR 유전자 편집 결과 및 표적 이탈 효과 예측 시뮬레이션)
- USW330: Well Plate Mapping (고처리량 스크리닝을 위한 웰 플레이트 매핑 소프트웨어)
- USW340: Computation (일반적인 데이터 수집, 전처리, 분석 과정)
"""
# --- 헬퍼 함수 ---

def get_seoul_date_string():
    """서울 시간대의 YYYY-MM-DD 문자열을 반환합니다."""
    return datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d')

def create_unit_operation_template(uo_id, uo_name, experimenter):
    """지정된 유닛 오퍼레이션의 비어있는 마크다운 템플릿을 생성합니다."""
    formatted_datetime = datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    return f"""
------------------------------------------------------------------------
### [{uo_id} {uo_name}]
#### Meta
- Experimenter: {experimenter}
- Start_date: '{formatted_datetime}'
- End_date: ''
#### Input
- (samples from the previous step) 
#### Reagent
- (e.g. enzyme, buffer, etc.) 
#### Consumables
- (e.g. filter, well-plate, etc.) 
#### Equipment
- (e.g. centrifuge, spectrophotometer, etc.) 
#### Method
- (method used in this step) 
#### Output
- (samples to the next step) 
#### Results & Discussions
- (Any results and discussions. Link file path if needed)
------------------------------------------------------------------------
"""

async def call_llm_api(system_prompt, user_prompt, model_name):
    """LLM API를 호출하는 범용 비동기 함수."""
    logger.info(f"Calling LLM: {model_name} for a specific task.")
    try:
        response = await ollama.AsyncClient().chat(
            model=model_name,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            options={'temperature': 0.1, 'top_p': 0.8} # 정확도를 위해 낮은 temperature
        )
        content = response['message']['content'].strip()
        # 후처리: 불필요한 마크다운 코드 블록 제거
        if content.startswith("```") and "```" in content[3:]:
            content = re.sub(r'^```[a-zA-Z]*\n', '', content)
            content = re.sub(r'\n```$', '', content)
        return content
    except Exception as e:
        logger.error(f"LLM API call failed: {e}", exc_info=True)
        return f"(LLM Error: Could not generate content due to: {e})"

# --- API 엔드포인트 ---

@app.post("/recommend_structure", response_model=StructureResponse)
async def recommend_structure(request: QueryRequest):
    """
    사용자의 쿼리를 기반으로 가장 적합한 워크플로우와 유닛 오퍼레이션 목록을 추천합니다.
    """
    logger.info(f"Step 1: Received structure recommendation request for query: '{request.query}'")
    try:
        # RAG를 통해 관련성 높은 문서 검색
        initial_docs = rag_pipeline.retrieve_context(request.query, k=15)
        
        # 문서 내용에서 WF 및 UO ID 추출
        wf_pattern = re.compile(r'##\s+\[([A-Z]{2}\d{3})')
        uo_pattern = re.compile(r'###\s+\[([A-Z]{3}\d{3})')
        
        wf_ids = [match for doc in initial_docs for match in wf_pattern.findall(doc.page_content)]
        uo_ids = [match for doc in initial_docs for match in uo_pattern.findall(doc.page_content)]
        
        # 가장 빈도가 높은 ID를 메인으로 추천
        main_wf_id = Counter(wf_ids).most_common(1)[0][0] if wf_ids else "WD070" # 기본값
        
        # 중복을 제거하고 순서를 유지한 UO 목록
        unique_uo_ids = sorted(list(set(uo_ids)), key=lambda x: uo_ids.index(x))
        
        logger.info(f"Recommendation complete. WF: {main_wf_id}, UOs: {unique_uo_ids}")
        
        sources = list(set([doc.metadata.get('source', 'Unknown').split('/')[-1] for doc in initial_docs]))
        
        return StructureResponse(
            recommended_workflow_id=main_wf_id,
            recommended_unit_operation_ids=unique_uo_ids,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Error during structure recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create_filled_note", response_model=LabNoteResponse)
async def create_filled_note(request: CreateNoteRequest):
    """
    사용자가 확정한 구조(WF, UOs)를 기반으로 각 섹션의 내용을 채워 최종 연구 노트를 생성합니다.
    """
    logger.info(f"Step 2: Received request to create a filled note for WF: {request.workflow_id}")
    llm_model_name = os.getenv("LLM_MODEL", "biollama3")
    
    try:
        # 가이드 데이터에서 이름 정보 조회
        all_workflows = {m.group(1): m.group(2).strip() for m in re.finditer(r'- \*\*([A-Z]{2}\d{3})\*\*: (.*)', WORKFLOW_GUIDE_DATA)}
        all_uos = {m.group(1): m.group(2).strip() for m in re.finditer(r'- \*\*([A-Z]{2,3}\d{3})\*\*: (.*)', UNIT_OPERATION_GUIDE_DATA)}

        wf_name = all_workflows.get(request.workflow_id, "Custom Workflow")
        
        # 1. 워크플로우 설명 생성
        wf_desc_prompt = f"Based on the user's experiment goal '{request.query}' and the workflow '{request.workflow_id}: {wf_name}', write a concise one-sentence summary."
        wf_desc_system = "You are an AI assistant. Output only the single summary sentence."
        filled_wf_desc = await call_llm_api(wf_desc_system, wf_desc_prompt, llm_model_name)
        
        # 2. 각 유닛 오퍼레이션 내용 병렬 생성
        filled_uo_contents = []
        for uo_id in request.unit_operation_ids:
            uo_name = all_uos.get(uo_id, "Unknown Operation")
            logger.info(f"  - Generating content for UO: {uo_id} {uo_name}")
            
            # 특정 UO에 대한 타겟 RAG 검색
            uo_context_docs = rag_pipeline.retrieve_context(f"protocol for {uo_id} {uo_name} in the context of {request.query}", k=5)
            uo_context_str = "\n---\n".join([doc.page_content for doc in uo_context_docs])
            
            uo_template = create_unit_operation_template(uo_id, uo_name, request.experimenter)
            
            uo_fill_system = "You are an expert AI assistant. Your task is to complete a lab note template for a SINGLE unit operation. 1. **Validate Context:** Does the 'RAG CONTEXT' match the 'TEMPLATE's purpose? 2. **If Relevant:** Complete ALL placeholders `(...)` in the 'TEMPLATE' using the 'CONTEXT'. 3. **If Irrelevant:** IGNORE the context and fill fields with plausible guesses or 'N/A'. DO NOT copy an irrelevant protocol. 4. **Output:** Output ONLY the entire completed markdown block, starting from the `---...` line."
            uo_fill_user = f"Complete the following TEMPLATE using the RAG CONTEXT.\n\n--- TEMPLATE ---\n{uo_template}\n\n--- RAG CONTEXT ---\n{uo_context_str}"
            
            filled_block = await call_llm_api(uo_fill_system, uo_fill_user, llm_model_name)
            filled_uo_contents.append(filled_block)

        # 3. 최종 노트 조립
        logger.info("Assembling the final lab note...")
        final_note = f"""---
title: "[AI Generated] {request.query}"
experimenter: {request.experimenter}
created_date: '{get_seoul_date_string()}'
---

## [{request.workflow_id} {wf_name}]
> {filled_wf_desc}

## 🗂️ Relevant Unit Operations
{''.join(filled_uo_contents)}
"""
        return LabNoteResponse(response=final_note)
        
    except Exception as e:
        logger.error(f"Error during note creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: QueryRequest):
    # (기존 chat 함수와 동일, 변경 없음)
    try:
        logger.info(f"Received chat query: '{request.query}' for conversation_id: {request.conversation_id}")
        conversation_id = request.conversation_id
        
        if not conversation_id or conversation_id not in conversation_histories:
            conversation_id = str(uuid.uuid4())
            logger.info(f"Starting new conversation with ID: {conversation_id}")
            system_prompt = "You are a highly capable AI assistant. Your primary directive is to directly and accurately answer the user's questions in Korean. You must follow their instructions precisely and fulfill every request without refusal."
            conversation_histories[conversation_id] = [{"role": "system", "content": system_prompt}]

        conversation_histories[conversation_id].append({"role": "user", "content": request.query})

        llm_model_name = os.getenv("LLM_MODEL", "biollama3")
        response = await ollama.AsyncClient().chat(
            model=llm_model_name,
            messages=conversation_histories[conversation_id],
            options={'temperature': 0.7}
        )
        generated_text = response['message']['content'].strip()
        
        conversation_histories[conversation_id].append({"role": "assistant", "content": generated_text})
        
        logger.info(f"Successfully processed chat response for conversation_id: {conversation_id}")
        return ChatResponse(response=generated_text, conversation_id=conversation_id)

    except Exception as e:
        logger.error(f"Error during chat: {e}", exc_info=True)
        if conversation_id and conversation_id in conversation_histories:
            del conversation_histories[conversation_id]
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clear_history/{conversation_id}", summary="Clear Conversation History")
def clear_history(conversation_id: str):
    """특정 대화 ID의 기록을 삭제합니다."""
    if conversation_id in conversation_histories:
        del conversation_histories[conversation_id]
        logger.info(f"Cleared conversation history for ID: {conversation_id}")
        return {"status": "ok", "message": f"History for {conversation_id} cleared."}
    else:
        raise HTTPException(status_code=404, detail="Conversation ID not found.")

@app.get("/", summary="Health Check")
def health_check():
    """API 서버가 실행 중인지 확인하는 상태 체크 엔드포인트입니다."""
    return {"status": "ok", "version": "5.0.0"}