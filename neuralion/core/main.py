from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI(title="Neuralion Core")

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "neuralion-core"}

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

@app.post("/chat")
def chat(req: ChatRequest):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are Neuralion. Be concise, helpful, and structured."},
            {"role": "user", "content": req.message},
        ],
        "stream": False,
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()

    # Ollama returns: { message: { role, content }, ... }
    return {"reply": data["message"]["content"]}