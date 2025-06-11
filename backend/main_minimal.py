from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello Railway", "port": os.getenv("PORT", "unknown")}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/test")
def test():
    return {"test": "working", "env_vars": dict(os.environ)} 