# GEMINI.md (v2.2)

## LabNote AI 2.0: 상호작용 기반의 자가 학습형 연구노트 시스템 구축 계획

### 1\. 프로젝트 비전

**정적(Static) 생성에서 동적(Interactive) 협업으로.**
LabNote AI의 목표는 단순히 문서를 생성하는 것을 넘어, 연구자와 상호작용하며 함께 노트를 완성하는 **협업 파트너**로 진화하는 것입니다. 1단계로 연구노트의 구조를 확립하고, 2단계에서 연구원이 원하는 특정 섹션을 선택하면 LangGraph 멀티 에이전트 팀이 해당 부분에 대한 전문적인 초안을 여러 개 제안합니다. 3단계에서는 연구원의 선택을 DPO(Direct Preference Optimization) 데이터로 학습하여, 시스템이 스스로 똑똑해지는 **지능형 선순환(Intelligent Flywheel)** 구조를 완성합니다.

-----

### 2\. 시스템 아키텍처 (섹션별 순환 모델)

사용자가 원할 때마다 특정 섹션을 채우고 피드백을 기록하는 순환적(Iterative) 워크플로우를 유지합니다.

```mermaid
graph TD
    subgraph Phase 1: 구조 생성 (Scaffolding)
        A[1. VSCode에서 '연구노트 생성' 실행] --> B{사용자가 WF/UO 선택};
        B --> C[2. FastAPI: /create_scaffold 호출];
        C --> D[3. 비어있는 .md 파일 생성];
    end

    subgraph Phase 2 & 3: 내용 채우기 및 학습 (Iterative Population & DPO)
        E[4. 사용자가 특정 UO의 특정 섹션 선택] -- in VSCode --> F(5. FastAPI: /populate_section 호출);
        F -- section, uo_id, file_content --> G[Supervisor Agent];
        G -- Routing --> H[Specialist Agent (Method, Materials, etc.)];
        H -- 🧠 Context-Aware RAG/LLM 호출 --> I[7. 옵션 2~3개 생성];
        I --> J{8. VSCode QuickPick에 옵션 표시};
        J -- 사용자가 최종안 선택 --> K[9. 에디터에 선택 내용 삽입];
        K --> L[10. FastAPI: /record_preference 호출];
        L -- 🧠 Context-Aware Prompt --> M[11. Redis에 DPO 데이터셋 저장];
        M --> E;
        M -- 주기적 학습 --> N[DPO 파이프라인];
        N --> O[✨개선된 BioLLM v2✨];
    end

    D -- 사용자가 작업 시작 --> E;
    K --> P[완성된 연구노트];

```

### 3\. 단계별 실행 계획 (Action Items)

| 단계 | 이름 | 상태 | 설명 |
|------|------|------|------|
| **Phase 1** | 구조 생성 | ✅ 완료 | `create_scaffold` 워크플로우가 안정적으로 동작하며 연구노트 기본 템플릿을 생성합니다. |
| **Phase 2** | 섹션별 내용 채우기 | ✅ 완료 | VSCode 커서 위치 기반으로 `populateSection` 명령 실행 → RAG + LLM 프롬프트 동적 생성. DPO 데이터 정상 수집 중. |
| **Phase 3** | DPO 파이프라인 | ✅ 완료 | 강화된 문맥 기반 프롬프트로 DPO 데이터를 Redis에 저장. `run_dpo_training.py`는 유연한 인자 지원으로 학습 가능. |
| **Phase 4** | 최종 UX 개선 및 배포 준비 | ✅ 완료 | VSCode 확장의 정규식 버그 수정, Webview UI 개선, 배포 자동화 스크립트 완성. |
| **Phase 5** | 서버 안정화 및 최적화 | 🚀 다음 단계 | 백엔드 성능·안정성 최적화를 통해 API 응답 속도 및 장애 대응력을 극대화합니다. |

#### **Phase 6: 최종 UX 개선 및 배포 (Final Step 🚀)**

**목표**: 현재의 `QuickPick` 기반 UI를 넘어, 더 풍부한 정보를 제공하고 사용 편의성을 극대화하는 UI를 도입하여 프로젝트를 완성합니다.

1.  **VSCode Webview를 이용한 옵션 표시 UI 개선 (`extension.ts`)**
    * **Action**: 현재 텍스트 미리보기만 가능한 `QuickPick` 메뉴를 **Webview UI**로 업그레이드합니다.
    * **구현**:
        1.  `/populate_note` API 호출 후, 반환된 옵션을 Webview 내에 각각의 카드(Card) 형태로 표시합니다.
        2.  각 카드에는 명확한 제목을 붙여줍니다. 
        3.  사용자가 Webview 내에서 카드를 선택하고 '적용' 버튼을 누르면, 해당 내용이 에디터에 삽입되고 DPO 데이터가 기록되도록 로직을 연결합니다. 이는 사용자에게 훨씬 직관적인 경험을 제공할 것입니다.

1.  **DPO 모델 배포 자동화 스크립트 작성 (`scripts/deploy_model.sh`)**
    * **Action**: DPO 학습 완료 후, 수동으로 진행해야 하는 GGUF 변환 및 Ollama 등록 과정을 자동화하는 셸 스크립트를 작성합니다.
    * **구현**:
        1.  `run_dpo_training.py`가 완료되면, 이 스크립트는 `llama.cpp`를 사용하여 학습된 모델을 GGUF로 변환합니다.
        2.  GGUF 파일을 기반으로 새로운 `Modelfile`을 동적으로 생성합니다.
        3.  `ollama create biollama3:v2 -f new_modelfile` 명령을 실행하여 새 모델을 Ollama에 등록합니다.
        4.  `.env` 파일의 `LLM_MODEL`을 새 버전으로 자동 업데이트하는 옵션을 제공합니다.

2.  **최종 문서화 및 정리 (`README.md`)**
    * **Action**: 새로운 기능(섹션 채우기, DPO)에 대한 사용법을 `README.md`에 추가하고, 전체 프로젝트 구조와 실행 방법을 최신 상태로 업데이트합니다.

이 마지막 단계를 완료하면, LabNote AI 2.0은 기술적으로 완성도 높은 프로젝트가 될 뿐만 아니라, 실제 연구 환경에서 매우 유용하게 사용될 수 있는 강력한 도구가 될 것입니다.