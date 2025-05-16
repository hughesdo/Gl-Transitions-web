from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import tempfile
import json
from shader_merger import ShaderVideoMerger

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SHADER_DIR = Path("./shaders")
TEMP_DIR = Path(tempfile.gettempdir())
# Load shader config
SHADER_CONFIG_PATH = SHADER_DIR / "shader_config.json"
SHADER_CONFIG = {}
if SHADER_CONFIG_PATH.exists():
    with open(SHADER_CONFIG_PATH, "r") as f:
        SHADER_CONFIG = json.load(f)

@app.get("/shaders/list")
async def list_shaders():
    shader_files = [f.name for f in SHADER_DIR.glob("*.glsl")]
    return JSONResponse(shader_files)

@app.get("/shaders/config")
async def shader_config():
    return JSONResponse(SHADER_CONFIG)

@app.post("/merge")
async def merge_videos(request: Request):
    form = await request.form()
    video1 = form['video1']
    video2 = form['video2']
    shader = form['shader']
    duration = float(form['duration'])
    # parse extra uniforms
    extra_uniforms = {}
    for key, value in form.items():
        if key.startswith("uniform_"):
            name = key[len("uniform_"):]
            try:
                extra_uniforms[name] = json.loads(value)
            except:
                extra_uniforms[name] = float(value)
    # Save uploaded files
    temp1 = TEMP_DIR / f"input1_{video1.filename}"
    temp2 = TEMP_DIR / f"input2_{video2.filename}"
    out_path = TEMP_DIR / "merged_output.mp4"
    with open(temp1, "wb") as f:
        shutil.copyfileobj(video1.file, f)
    with open(temp2, "wb") as f:
        shutil.copyfileobj(video2.file, f)
    # Run merger
    shader_path = SHADER_DIR / shader
    merger = ShaderVideoMerger(
        video1_path=temp1,
        video2_path=temp2,
        shader_path=shader_path,
        duration_sec=duration,
        output_path=out_path,
        extra_uniforms=extra_uniforms
    )
    merger.run()
    return FileResponse(out_path, media_type="video/mp4", filename="merged_output.mp4")

from fastapi.responses import HTMLResponse
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return Path("index.html").read_text()
