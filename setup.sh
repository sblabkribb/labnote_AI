#!/bin/bash
# This script sets up the complete AI backend environment on a VESSL Workspace.
# Version 3.4: Added idempotency checks to skip already completed steps for faster restarts.
set -e

# --- 1. System & Prerequisite Setup ---
echo ">>> (Step 1/5) Updating package lists and installing prerequisites..."
apt-get update > /dev/null
apt-get install -y curl > /dev/null
pip install -q huggingface_hub[cli]
echo ">>> Prerequisites are up to date."

# --- 2. Redis Stack Server Setup ---
if ! command -v redis-stack-server &> /dev/null
then
    echo ">>> (Step 2/5) Redis not found. Installing Redis Stack Server..."
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list > /dev/null
    apt-get update > /dev/null
    apt-get install -y redis-stack-server > /dev/null
    redis-stack-server --daemonize yes
    echo ">>> Redis Stack Server installed and started."
else
    echo ">>> (Step 2/5) Redis is already installed. Skipping."
    # Ensure it's running
    if ! pgrep -f redis-stack-server > /dev/null; then
        redis-stack-server --daemonize yes
        echo ">>> Redis Stack Server was not running, so it has been started."
    fi
fi

# --- 3. Ollama Server Setup & Robust Wait ---
if ! command -v ollama &> /dev/null
then
    echo ">>> (Step 3/5) Ollama not found. Installing and starting Ollama server..."
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    sleep 5
    echo ">>> Waiting for Ollama server to be fully ready..."
    ollama pull nomic-embed-text # Use this as a readiness check
    echo ">>> Ollama server is confirmed to be ready!"
else
    echo ">>> (Step 3/5) Ollama is already installed. Skipping installation."
    if ! pgrep -f "ollama serve" > /dev/null; then
        ollama serve &
        sleep 5 # Give it a moment to start
        echo ">>> Ollama server was not running, so it has been started."
    fi
fi


# --- 4. Main LLM Download and Setup ---
MODEL_NAME="biollama3"
MODEL_FILE_PATH="/models/Llama3-OpenBioLLM-8B.f16.gguf"

if [ ! -f "$MODEL_FILE_PATH" ]; then
    echo ">>> (Step 4/5) Model file not found. Downloading Llama3-OpenBioLLM-8B (F16)..."
    huggingface-cli download mradermacher/Llama3-OpenBioLLM-8B-GGUF \
        Llama3-OpenBioLLM-8B.f16.gguf \
        --local-dir /models --local-dir-use-symlinks False
    echo ">>> Model downloaded."
else
    echo ">>> (Step 4/5) Model file already exists. Skipping download."
fi

if ! ollama list | grep -q "$MODEL_NAME"; then
    echo ">>> Creating Modelfile for '$MODEL_NAME'..."
    cat <<'EOF' > /models/Modelfile
FROM /models/Llama3-OpenBioLLM-8B.f16.gguf
TEMPLATE """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
EOF
    
    echo ">>> Creating custom model '$MODEL_NAME' with Ollama..."
    ollama create "$MODEL_NAME" -f /models/Modelfile
    echo ">>> '$MODEL_NAME' model created."
else
    echo ">>> Custom model '$MODEL_NAME' already exists. Skipping creation."
fi

# --- 5. FastAPI Backend Setup and Launch ---
echo ">>> (Step 5/5) Setting up and launching FastAPI backend..."
cd labnote-ai-backend
pip install -r requirements.txt
echo ">>> Backend dependencies are up to date."

echo ">>> Starting Uvicorn server on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000

