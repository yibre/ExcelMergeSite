import os
import shutil

from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import HTMLResponse

# API router 세팅 및 html template 연결
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Configuration
UPLOADS_DIR = "uploads"

# Upload directory가 없으면 만들기
os.makedirs(UPLOADS_DIR, exist_ok=True)

# request는 Jinja2에서 늘 들어가야함
@router.get("/test", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("world.html", {"request": request, "message": "Hello, World!"})


@router.get("/main", response_class=HTMLResponse)
async def main_page(request : Request):
    """
    메인 페이지 렌더링용
    메인화면 : 파일 합치는 표
    """
     # List all files in the uploads directory
    try:
        files = os.listdir(UPLOADS_DIR)
    except OSError:
        files = []
        
    context = {
        "request": request,
        "title": "Home Page - File Uploader",
        "message": "Upload your Excel file below. All uploaded files are available for download by any user.",
        "files": files
    }
    return templates.TemplateResponse("home.html", context)


@router.post("/upload", response_class=HTMLResponse)
async def handle_upload(file: UploadFile = File(...)):
    pass