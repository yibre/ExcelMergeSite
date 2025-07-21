import os
import shutil
import openpyxl

from typing import Optional
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, File, UploadFile, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# API router 세팅 및 html template 연결
router = APIRouter()
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")

# --- Configuration ---
UPLOADS_DIR = "uploads"
VERSIONS = ["ver1", "ver2"]
TEMPLATE_FILENAME = "template.xlsx"
MASTER_FILENAME = "master.xlsx" 

# Upload directory가 없으면 만들기 & 버전별로 다르게 짜기
os.makedirs(UPLOADS_DIR, exist_ok=True)
for version in VERSIONS:
    os.makedirs(os.path.join(UPLOADS_DIR, version), exist_ok=True)


def get_version_dir(version: str):
    """버전별로 다른 기능 제공"""
    return os.path.join(UPLOADS_DIR, version)


# request는 Jinja2에서 늘 들어가야함
@router.get("/test", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("world.html", {"request": request, "message": "Hello, World!"})


@router.get("/", response_class=HTMLResponse)
async def main_page(request : Request, version: Optional[str] = Query("ver1")):
    """
    메인 페이지 렌더링용
    메인화면 : 파일 합치는 표
    """
    if version not in VERSIONS:
        version = "ver1" # Default to ver1 if an invalid version is passed
    
    version_dir = get_version_dir(version)
    try:
        all_files = os.listdir(version_dir)
        template_file = TEMPLATE_FILENAME if TEMPLATE_FILENAME in all_files else None
        master_file = MASTER_FILENAME if MASTER_FILENAME in all_files else None
        data_files = [f for f in all_files if f not in [TEMPLATE_FILENAME, MASTER_FILENAME]]
    except OSError:
        template_file = None
        master_file = None
        data_files = []
        
    context = {
        "request": request,
        "title": f"File Manager - {version.upper()}",
        "versions": VERSIONS,
        "current_version": version,
        "template_file": template_file,
        "master_file": master_file,
        "data_files": data_files,
        "master_filename_const": MASTER_FILENAME
    }
    return templates.TemplateResponse("home.html", context)



@router.post("/upload_template/{version}", response_class=RedirectResponse)
async def handle_upload_template(version:str, file: UploadFile = File(...)):
    """
    template.xlsx 올리는 기능
    이 버튼을 통해 올린 것은 template.xlsx로만 저장됨
    """
    file_path = os.path.join(get_version_dir(version), TEMPLATE_FILENAME)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url=f"/?version={version}", status_code=303)

@router.post("/upload_master/{version}", response_class=RedirectResponse)
async def handle_upload_master(version: str, file: UploadFile = File(...)):
    file_path = os.path.join(get_version_dir(version), MASTER_FILENAME)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url=f"/?version={version}", status_code=303)



@router.post("/upload/{version}", response_class=RedirectResponse)
async def handle_upload(version: str, file: UploadFile = File(...)):
    """
    파일 업로드 관리
    업로드한 파일을 프로젝트 내 /uploads 디렉터리에 보관
    """
    file_path = os.path.join(get_version_dir(version), file.filename)
    if file.filename in [TEMPLATE_FILENAME, MASTER_FILENAME]:
        return HTMLResponse(content=f"Cannot upload a data file with a reserved name. Please use the dedicated upload buttons.", status_code=400)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url=f"/?version={version}", status_code=303)


@router.get("/download/{version}/{filename}", response_class=FileResponse)
async def handle_download(version: str, filename: str):
    """
    파일 옆 다운로드 버튼 누르면 다운로드됨
    """
    file_path = os.path.join(get_version_dir(version), filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=filename)
    return HTMLResponse(content="File not found.", status_code=404)



@router.get("/delete/{version}/{filename}", response_class=RedirectResponse)
async def handle_delete(version: str, filename: str):
    """
    파일 옆 x 버튼 누르면 해당 파일 삭제 가능
    upload 파일에 있는 내용을 알아서 삭제함
    """
    file_path = os.path.join(get_version_dir(version), filename)
    if ".." in filename or filename.startswith("/"):
        return HTMLResponse(content="Invalid filename.", status_code=400)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error deleting file {filename}: {e}")
    return RedirectResponse(url=f"/?version={version}", status_code=303)



@router.get("/merge", response_class=FileResponse)
async def merge_files():
    """
    엑셀 파일을 template 파일에 합치기
    """
    template_path = os.path.join(UPLOADS_DIR, TEMPLATE_FILENAME)
    output_filename = "merged_output.xlsx"
    output_path = os.path.join(UPLOADS_DIR, output_filename)

    if not os.path.exists(template_path):
        return HTMLResponse(content=f"Template file '{TEMPLATE_FILENAME}' not found. Please upload it first.", status_code=404)

    # Load the template and get its header
    merged_wb = openpyxl.load_workbook(template_path)
    merged_ws = merged_wb.active
    template_header = [cell.value for cell in merged_ws[1]]

    files_to_merge = [f for f in os.listdir(UPLOADS_DIR) if f.endswith('.xlsx') and f not in [TEMPLATE_FILENAME, output_filename, MASTER_MERGE_FILENAME]]

    for filename in files_to_merge:
        filepath = os.path.join(UPLOADS_DIR, filename)
        source_wb = openpyxl.load_workbook(filepath)
        source_ws = source_wb.active
        
        header_found = False
        # Find the header row in the source file
        for row_idx, row in enumerate(source_ws.iter_rows(values_only=True), 1):
            if list(row) == template_header:
                header_found = True
                # Start copying data from the row *after* the header
                for data_row in source_ws.iter_rows(min_row=row_idx + 1, values_only=True):
                    if any(cell is not None for cell in data_row):
                        merged_ws.append(data_row)
                break # Move to the next file once data is copied
        
        if not header_found:
            print(f"Warning: Header not found in {filename}. File skipped.")

    merged_wb.save(output_path)
    return FileResponse(path=output_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=output_filename)



@router.get("/download_my_data/{version}/{original_filename}")
async def download_my_data(version: str, original_filename: str):
    """
    마스터 파일 올리면 분할 후 다시 다운로드 시작
    """
    version_dir = get_version_dir(version)
    master_path = os.path.join(version_dir, MASTER_FILENAME)
    user_file_path = os.path.join(version_dir, original_filename)

    if not os.path.exists(master_path):
        return HTMLResponse(content=f"Master file '{MASTER_FILENAME}' not found. Please upload it first.", status_code=404)
    if not os.path.exists(user_file_path):
        return HTMLResponse(content=f"Original user file '{original_filename}' not found.", status_code=404)

    try:
        user_wb = openpyxl.load_workbook(user_file_path)
        user_ws = user_wb.active
        key_value = user_ws['B2'].value
        if key_value is None:
            return HTMLResponse(content=f"Could not find a key value in cell B2 of '{original_filename}'.", status_code=400)

        filtered_wb = openpyxl.Workbook()
        filtered_ws = filtered_wb.active
        
        master_wb = openpyxl.load_workbook(master_path)
        master_ws = master_wb.active
        header = [cell.value for cell in master_ws[1]]
        filtered_ws.append(header)

        for row in master_ws.iter_rows(min_row=2, values_only=True):
            if len(row) > 1 and row[1] == key_value:
                filtered_ws.append(row)
        
        output_filename = f"filtered_for_{key_value}.xlsx"
        output_path = os.path.join(version_dir, output_filename)
        filtered_wb.save(output_path)

        return FileResponse(path=output_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=output_filename)

    except Exception as e:
        print(f"An error occurred: {e}")
        return HTMLResponse(content=f"An error occurred during processing: {e}", status_code=500)
