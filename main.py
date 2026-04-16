import asyncio
import json
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, StreamingResponse
from analyzer.code_analyzer import analyze_code
from analyzer.prompts import SUPPORTED_LANGUAGES
from analyzer.report import generate_pdf_report
from analyzer.test_runner import generate_and_run_tests

app = FastAPI(title="AutoFix AI", version="4.0.0")

MAX_FILE_SIZE = 500 * 1024  # 500KB
ALLOWED_EXTENSIONS = set(SUPPORTED_LANGUAGES.keys())

# Store uploaded files temporarily for SSE analysis
pending_files = {}

app.mount("/static", StaticFiles(directory="static"), name="static")


def validate_file(filename: str, content: bytes) -> str:
    """Validate uploaded file and return decoded code."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported: {supported}")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 500KB.")
    try:
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text.")
    if not code.strip():
        raise HTTPException(status_code=400, detail="File is empty.")
    return code


@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "AutoFix AI", "version": "3.0.0"}


@app.get("/api/languages")
async def get_supported_languages():
    return {"extensions": list(ALLOWED_EXTENSIONS), "languages": list(set(SUPPORTED_LANGUAGES.values()))}


@app.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()
    code = validate_file(file.filename, content)
    result = await analyze_code(file.filename, code)
    return result


@app.post("/api/analyze-stream")
async def analyze_stream_upload(file: UploadFile = File(...)):
    """Upload file and get a job_id for SSE streaming."""
    content = await file.read()
    code = validate_file(file.filename, content)
    job_id = str(uuid.uuid4())[:8]
    pending_files[job_id] = {"filename": file.filename, "code": code}
    return {"job_id": job_id}


@app.get("/api/analyze-stream/{job_id}")
async def analyze_stream_sse(job_id: str):
    """SSE endpoint that streams progress updates."""
    if job_id not in pending_files:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = pending_files.pop(job_id)

    async def event_generator():
        progress_queue = asyncio.Queue()

        async def progress_callback(step, status, detail):
            await progress_queue.put({"step": step, "status": status, "detail": detail})

        async def run_analysis():
            result = await analyze_code(job["filename"], job["code"], progress_callback=progress_callback)
            await progress_queue.put({"step": "result", "status": "done", "data": result})

        task = asyncio.create_task(run_analysis())

        while True:
            msg = await progress_queue.get()
            if msg["step"] == "result":
                yield f"data: {json.dumps(msg['data'], ensure_ascii=False)}\n\n"
                break
            else:
                yield f"event: progress\ndata: {json.dumps(msg)}\n\n"

        await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/test-cases")
async def generate_tests(file: UploadFile = File(...)):
    """Generate and execute test cases for uploaded code."""
    content = await file.read()
    code = validate_file(file.filename, content)
    result = await generate_and_run_tests(file.filename, code)
    return result


@app.post("/api/report")
async def download_report(file: UploadFile = File(...)):
    content = await file.read()
    code = validate_file(file.filename, content)
    result = await analyze_code(file.filename, code)
    pdf_bytes = generate_pdf_report(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=autofix_report_{file.filename}.pdf"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
