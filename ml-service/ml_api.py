import base64
import io
import os
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from PIL import Image

import torch
from facenet_pytorch import InceptionResnetV1, MTCNN

app = FastAPI()

# --- Simple API key auth (recommended) ---
API_KEY = os.getenv("ML_API_KEY", "")

def require_key(req: Request):
    if not API_KEY:
        return  # allow if not set (dev)
    got = req.headers.get("x-ml-key", "")
    if got != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Load model once at startup
device = "cpu"
mtcnn = MTCNN(image_size=160, margin=0, device=device)
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

class EmbedReq(BaseModel):
    image_base64: str  # raw base64, or data URL

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/embed")
def embed(req: EmbedReq, request: Request):
    require_key(request)

    img_b64 = req.image_base64
    # accept data URL
    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(img_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64")

    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")

    face = mtcnn(img)
    if face is None:
        return {"ok": False, "error": "no_face"}

    with torch.no_grad():
        emb = model(face.unsqueeze(0)).squeeze(0).cpu().numpy().astype(np.float32)

    # normalize
    emb = emb / (np.linalg.norm(emb) + 1e-12)
    return {"ok": True, "embedding": emb.tolist()}
