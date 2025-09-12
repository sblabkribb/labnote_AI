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

---

### 4\.: 서버 안정화 및 최적화 (Next Step)

### 목표
- **API 응답 성능 최적화**
- **에러 처리 명확화**
- **반복적 리소스 소비 제거**
- **Redis 연결 안정성 강화**

---

### ✅ Action Item 1: 에러 처리 강화 (`main.py`)

#### 문제
`/record_preference` 엔드포인트에서 예외 발생 시 `pass`로 조용히 무시되어 클라이언트에 오류 정보가 전달되지 않음.

#### 해결 방안
특정 예외(`RedisConnectionError`, etc.)를 명확히 캐치하고, HTTP 500 응답과 상세 메시지를 클라이언트에 반환.

#### `gemini.cli` 명령어
```bash
gemini modify labnote-ai-backend/main.py \
  --prompt "In the /record_preference endpoint, refactor the try...except block. Instead of 'pass' on exceptions like Redis connection errors, catch specific exceptions and raise an HTTPException with a 500 status code and a clear error message for the client."
```

---

### ✅ Action Item 2: 정규식 사전 컴파일 성능 최적화 (`main.py`)

#### 문제
`/record_preference` 내에서 매 요청마다 `re.compile()` 호출 → 불필요한 CPU 부하.

#### 해결 방안
정규식 패턴 `uo_block_pattern`을 **모듈 레벨**에서 한 번만 컴파일하고 재사용.

#### `gemini.cli` 명령어
```bash
gemini modify labnote-ai-backend/main.py \
  --prompt "Optimize performance by pre-compiling the regex pattern 'uo_block_pattern' used in the /record_preference endpoint. Move the re.compile() call to the module's top level so it is compiled only once when the application starts."
```

---

### ✅ Action Item 3: 데이터 사전 처리 최적화 (`main.py`)

#### 문제
매 요청마다 `UNIT_OPERATION_GUIDE_DATA`를 파싱해 `all_uos` 딕셔너리 생성 → 비효율적.

#### 해결 방안
애플리케이션 시작 시 **한 번만 파싱**하여 전역 변수 `ALL_UOS_DATA`로 저장, 이후 모든 요청에서 재사용.

#### `gemini.cli` 명령어
```bash
gemini modify labnote-ai-backend/main.py \
  --prompt "To improve performance, pre-process the UNIT_OPERATION_GUIDE_DATA at application startup. Create a global dictionary 'ALL_UOS_DATA' at the module level by parsing the guide data once. Then, refactor the /record_preference endpoint to use this pre-computed dictionary instead of parsing it on every request."
```

---

### 🔧 Action Item 4: Redis 연결 관리 개선 (선택적 심화 과제)

#### 문제
매 요청마다 새 Redis 연결 생성 → 연결 오버헤드 및 리소스 누수 가능성.

#### 해결 방안
FastAPI의 `lifespan` 이벤트를 활용해 **연결 풀(Connection Pool)** 을 애플리케이션 생명주기 동안 유지.

- 앱 시작 시 연결 풀 생성
- 앱 종료 시 정상 닫힘
- `/record_preference`는 풀에서 연결을 획득하여 사용

#### `gemini.cli` 명령어
```bash
gemini modify labnote-ai-backend/main.py \
  --prompt "For more robust connection management, implement a Redis connection pool using FastAPI's lifespan context manager. Create the connection pool when the app starts up and close it gracefully on shutdown. Refactor the /record_preference endpoint to get a connection from this pool."
```

---

## 💡 결론 및 향후 방향

| 항목 | 내용 |
|------|------|
| **핵심 가치** | 연구자의 의사결정을 학습 데이터로 삼아, 시스템이 스스로 더 나은 파트너가 되는 **자기 진화형 AI** |
| **기술적 우위** | LangGraph × DPO × Real-time VSCode 통합 = **연구 노트의 새로운 표준** |
| **차세대 목표** | DPO 학습 주기 자동화 → 주간/월간 모델 업데이트 파이프라인 구축 → **자동 실험 설계 추천** 기능 연계 |

> 🏁 **Phase 5 완료 후**, LabNote AI 2.0은 단순한 보조 도구가 아닌, **연구자의 사고를 확장하는 지능형 코디네이터**로 자리잡게 됩니다.
