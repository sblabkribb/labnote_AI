#!/bin/bash
# This script sets up the complete AI backend environment on a VESSL Workspace.
# Version 4.2: Corrected Hugging Face repository ID to 'mradermacher'.
set -e

# --- 1. System & Prerequisite Setup ---
echo ">>> (Step 1/5) Updating package lists and installing prerequisites..."
apt-get update > /dev/null
apt-get install -y curl > /dev/null
pip install -q huggingface_hub[cli]
echo ">>> Prerequisites are up to date."

# --- 2. Redis Stack Server Setup ---
echo ">>> (Step 2/5) Setting up Redis Stack Server..."
if ! command -v redis-stack-server &> /dev/null; then
    echo "    - Installing Redis..."
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list > /dev/null
    apt-get update > /dev/null
    apt-get install -y redis-stack-server > /dev/null
fi
if ! pgrep -f redis-stack-server > /dev/null; then
    redis-stack-server --daemonize yes
    echo ">>> Redis Stack Server started."
else
    echo ">>> Redis is already running."
fi

# --- 3. Ollama and Required Models Setup ---
echo ">>> (Step 3/5) Setting up Ollama and models..."
if ! command -v ollama &> /dev/null; then
    echo "    - Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "    - Starting Ollama server in background..."
    ollama serve &
    sleep 5 # Give it a moment to initialize
fi

echo "    - Verifying and pulling 'nomic-embed-text' model (used for readiness check)..."
ollama pull nomic-embed-text > /dev/null
echo ">>> Ollama server and embedding model are ready."

# --- 4. Main LLM Download and Setup ---
MODEL_NAME="biollama3"
MODEL_FILE_PATH="/models/Llama3-OpenBioLLM-8B.f16.gguf"
echo ">>> (Step 4/5) Setting up main LLM: ${MODEL_NAME}..."

if ! ollama list | grep -q "$MODEL_NAME"; then
    if [ ! -f "$MODEL_FILE_PATH" ]; then
        echo "    - Main model file not found. Downloading (~16GB)..."
        # ⬇️⬇️⬇️ 바로 이 부분! 저장소 주소를 'mradermacher'로 수정했습니다. ⬇️⬇️⬇️
        huggingface-cli download mradermacher/Llama3-OpenBioLLM-8B-GGUF \
            Llama3-OpenBioLLM-8B.f16.gguf \
            --local-dir /models --local-dir-use-symlinks False
    fi
    
    echo "    - Creating Modelfile for '${MODEL_NAME}'..."
    cat <<'EOF' > /models/Modelfile
FROM /models/Llama3-OpenBioLLM-8B.f16.gguf
TEMPLATE """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
EOF
    
    echo "    - Creating custom model with Ollama..."
    ollama create "$MODEL_NAME" -f /models/Modelfile
    echo ">>> Main LLM '${MODEL_NAME}' is ready."
else
    echo ">>> Main LLM '${MODEL_NAME}' already exists."
fi

# --- 5. FastAPI Backend Setup and Launch ---
echo ">>> (Step 5/5) Setting up and launching FastAPI backend..."
cd labnote-ai-backend
pip install -r requirements.txt > /dev/null
echo ">>> Backend dependencies installed."

echo ">>> Starting Uvicorn server on http://0.0.0.0:8000"
uvicorn main:app --host 0.0.0.0 --port 8000