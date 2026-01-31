# webhook_server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from pathlib import Path
import json

app = FastAPI(title="VisionSecure Alert Receiver")

LOG_DIR = Path("alert_logs")
LOG_DIR.mkdir(exist_ok=True, parents=True)

@app.post("/alert")
async def receive_alert(request: Request):
    body = await request.json()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    log_file = LOG_DIR / f"alert_{ts}.json"

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)

    print("Alerta recebido:")
    print(json.dumps(body, ensure_ascii=False, indent=2))

    return JSONResponse({"status": "ok", "message": "alert received"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
