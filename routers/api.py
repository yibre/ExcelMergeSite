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
async def read_home(request : Request):
    pass