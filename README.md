# LabNote AI Assistant: 바이오파운드리를 위한 혁신적인 AI 솔루션

이 프로젝트는 최신 AI 기술(BioMistral-7B, RAG, DPO)을 활용하여 과학자들을 위한 지능형 랩노트 어시스턴트를 구축하는 것을 목표로 합니다. 이 저장소는 로컬 개발 환경을 위한 완전한 코드 구조를 제공합니다.

## 프로젝트 구조
```bash
├── labnote-ai-backend/ # Python FastAPI 백엔드
│ ├── sops/ # 실험 SOP 문서 폴더
│ ├── main.py # API 서버 진입점
│ └── rag_pipeline.py # RAG 핵심 로직
├── ollama_custom_models/ # Ollama용 커스텀 모델 파일
├── vscode-labnote-extension/ # VS Code 확장 프로그램
└── docker-compose.yml # Ollama & Redis 컨테이너 설정
```


## 빠른 시작 가이드

### 1. 사전 준비
- **Docker Desktop** 설치 및 실행 (기타 다른 desktop 가능)
- **Python 3.10+** 설치
- **Node.js 18+** 및 **npm** 설치
- **VS Code** 설치
- **Ollama** 데스크탑 앱 설치 ([공식 사이트](https://ollama.com/))

### 2. Docker 컨테이너 실행 (Ollama & Redis)
터미널에서 프로젝트 루트 디렉토리로 이동한 후, 다음 명령어를 실행합니다.
```bash
docker-compose up -d
```
* Redis는 `localhost:6379`에서 실행됩니다.
* Ollama API는 `localhost:11434`에서 실행됩니다.

### 3. 커스텀 모델 등록 (Ollama)
`ollama_custom_models/` 디렉토리에 `Modelfile`과 `biomistral-7b.Q4_K_M.gguf` 파일이 준비되어 있어야 합니다. 공싱에서 다운 받거나 커스텀 모델 가능 (이름만 바꿔주시면 됩니다.) 터미널에서 다음 명령어를 실행합니다.

```bash
cd ollama_custom_models
ollama create biomistral -f Modelfile
``` 
### 4. Python 백엔드 설정
```bash
cd labnote-ai-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Python 백엔드 서버 실행
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
서버가 `http://127.0.0.1:8000`에서 실행됩니다. Swagger UI는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

## 6. VS Code 확장 프로그램 설치 및 실행
* 1. VS Code에서 `vscode-labnote-extension` 폴더를 엽니다.
* 2. 터미널에서 `npm install`을 실행하여 의존성을 설치합니다.
* 3. F5 키를 눌러 확장 프로그램을 디버그 모드로 실행합니다. 새로운 VS Code 창이 열립니다.
* 4. 새로운 VS Code 창에서 `Ctrl+Shift+P` (또는 `Cmd+Shift+P`)를 누르고 `LabNote AI: Generate Note` 명령어를 실행합니다.

## SOP 문서 추가
새로운 실험 프로토콜을 AI가 학습하도록 하려면, `labnote-ai-backend/sops/` 디렉토리에 .md 형식으로 파일을 추가한 후, 백엔드 서버를 재시작하면 자동으로 인덱싱됩니다.


## 