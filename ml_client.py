import os
import requests

ML_BASE_URL = os.getenv("ML_BASE_URL", "").rstrip("/")  # e.g. https://...run.app
ML_API_KEY = os.getenv("ML_API_KEY", "")               # same as Cloud Run

def get_embedding(image_base64: str):
    if not ML_BASE_URL:
        raise RuntimeError("ML_BASE_URL not set")

    headers = {}
    if ML_API_KEY:
        headers["x-ml-key"] = ML_API_KEY

    payload = {"image_base64": image_base64}

    r = requests.post(f"{ML_BASE_URL}/embed", json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()

    if not data.get("ok"):
        return None
    return data["embedding"]
