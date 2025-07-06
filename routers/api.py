from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

"""
@router.post("/files")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}

@router.post("/uploadfile")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}
"""

# request는 Jinja2에서 늘 들어가야함
@router.get("/test", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("world.html", {"request": request, "message": "Hello, World!"})