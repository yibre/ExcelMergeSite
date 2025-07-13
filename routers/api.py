import os
import shutil

from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

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
    """
    파일 업로드 관리
    업로드한 파일을 프로젝트 내 /uploads 디렉터리에 보관
    """
    file_path = os.path.join(UPLOADS_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 업로드 후 홈페이지로 redirection
    return RedirectResponse(url="/main", status_code=303)


@router.get("/download/{filename}", response_class=FileResponse)
async def handle_download(filename: str):
    """
    파일 옆 다운로드 기능 누르면 다운로드 가능
    """
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    # Check if file exists to prevent path traversal attacks and errors
    if os.path.exists(file_path):
        return FileResponse(path=file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=filename)
    
    # 없는 파일을 다운받으려고 할 때 : 404
    return HTMLResponse(content="File not found.", status_code=404)

@router.get("/delete/{filename}", response_class=FileResponse)
async def handle_delete(filename: str):
    """
    파일 옆 x 버튼 누르면 해당 파일 삭제 가능
    upload 파일에 있는 내용을 알아서 삭제함
    """
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    # path traversal을 통한 해킹 방지
    if ".." in filename or filename.startswith("/"):
        return HTMLResponse(content="Invalid filename.", status_code=400)

    # 파일 존재 유무 확인
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            # 에러 디텍션용 로깅
            print(f"Error deleting file {filename}: {e}")

    # 업데이트 리스트가 있는 메인 페이지로 돌아옴
    return RedirectResponse(url="/main", status_code=303)

@router.get("/merge", response_class=FileResponse)
async def merge_files():
    pass