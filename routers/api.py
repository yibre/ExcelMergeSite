import os
import shutil
import openpyxl
import json
from datetime import datetime
from fastapi import Request, UploadFile, File, APIRouter, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from routers.authentification import verify_ip_whitelist

# --- Configuration ---
UPLOADS_DIR = "uploads"
TEMPLATE_FILENAME = "template.xlsx"
MASTER_MERGE_FILENAME = "master.xlsx"
VERSIONS = ["ver1", "ver2"]
FILE_OWNERSHIP_PATH = "json/file_ownership.json"

os.makedirs(UPLOADS_DIR, exist_ok=True)
for version in VERSIONS:
    os.makedirs(os.path.join(UPLOADS_DIR, version), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, version, "results"), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, version, "masterdb"), exist_ok=True)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")


# ver1 용인지 ver2 용인지 리턴
def get_version_dir(version: str):
    """Helper to get the correct versioned directory path."""
    return os.path.join(UPLOADS_DIR, version)


# --- 파일 소유권 관리 함수들 ---
def load_file_ownership():
    """파일 소유권 정보 로드"""
    if os.path.exists(FILE_OWNERSHIP_PATH):
        with open(FILE_OWNERSHIP_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_file_ownership(data):
    """파일 소유권 정보 저장"""
    with open(FILE_OWNERSHIP_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def register_file_owner(version: str, filename: str, ip: str):
    """파일 업로드 시 소유자 IP 등록"""
    ownership = load_file_ownership()
    if version not in ownership:
        ownership[version] = {}
    ownership[version][filename] = ip
    save_file_ownership(ownership)

def check_file_owner(version: str, filename: str, ip: str) -> bool:
    """현재 IP가 해당 파일의 소유자인지 확인"""
    ownership = load_file_ownership()
    return ownership.get(version, {}).get(filename) == ip


@router.get("/", response_class=HTMLResponse)
async def read_home(request: Request, client_ip: str = Depends(verify_ip_whitelist)):
    """
    This endpoint serves the home page.
    It now separates the template file from the data files for display.
    """
    try:
        all_files = os.listdir(UPLOADS_DIR)
        files1 = os.listdir(UPLOADS_DIR+"/ver1")
        files2 = os.listdir(UPLOADS_DIR+"/ver2")
        template_file = TEMPLATE_FILENAME if TEMPLATE_FILENAME in all_files else None
        data_files1 = [f for f in files1 if f not in [TEMPLATE_FILENAME, 'merged_output_r1.xlsx']]
        data_files2 = [f for f in files2 if f not in [TEMPLATE_FILENAME, 'merged_output_r2.xlsx']]

        # results 폴더의 파일 리스트 가져오기
        results_files1 = os.listdir(UPLOADS_DIR+"/ver1/results")
        results_files2 = os.listdir(UPLOADS_DIR+"/ver2/results")

        # masterdb 폴더의 파일 리스트 가져오기
        masterdb_files1 = os.listdir(UPLOADS_DIR+"/ver1/masterdb")
        masterdb_files2 = os.listdir(UPLOADS_DIR+"/ver2/masterdb")
    except OSError:
        template_file = None
        data_files1 = []
        data_files2 = []
        results_files1 = []
        results_files2 = []
        masterdb_files1 = []
        masterdb_files2 = []

    # 삭제 가능 여부 판단 (일반 데이터 파일만)
    deletable_files1 = {f: check_file_owner("ver1", f, client_ip) for f in data_files1}
    deletable_files2 = {f: check_file_owner("ver2", f, client_ip) for f in data_files2}

    context = {
        "request": request,
        "title": "Home Page - File Uploader",
        "message": "Upload data files below. Use the dedicated button for the template.",
        "versions": VERSIONS,
        "template_file": template_file,
        "data_files1": data_files1, # ver1에 올라간 파일 리스트
        "data_files2": data_files2, # ver2에 올라간 파일 리스트
        "results_files1": results_files1, # ver1/results에 올라간 파일 리스트
        "results_files2": results_files2, # ver2/results에 올라간 파일 리스트
        "master_merge_filename": MASTER_MERGE_FILENAME,
        "deletable_files1": deletable_files1,
        "deletable_files2": deletable_files2,
        "masterdb_files1": masterdb_files1,
        "masterdb_files2": masterdb_files2
    }
    return templates.TemplateResponse("home.html", context)


@router.post("/upload_template", response_class=RedirectResponse)
async def handle_upload_template(
    file: UploadFile = File(...),
    client_ip: str = Depends(verify_ip_whitelist)
):
    """
    NEW: Dedicated endpoint for uploading the template.xlsx file.
    It will always be saved as 'template.xlsx'.
    """
    file_path = os.path.join(UPLOADS_DIR, TEMPLATE_FILENAME)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/", status_code=303)


@router.post("/upload_master/{version}", response_class=RedirectResponse)
async def handle_upload_master(
    version: str,
    file: UploadFile = File(...),
    client_ip: str = Depends(verify_ip_whitelist)
):
    now = datetime.now()
    timestamp = now.strftime("%y%m%d_%H시%M분")
    filename = f"master_{version}_{timestamp}.xlsx"
    results_dir = os.path.join(get_version_dir(version), "results")
    file_path = os.path.join(results_dir, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/", status_code=303)


@router.post("/upload/{version}", response_class=RedirectResponse)
async def handle_upload(
    version: str,
    file: UploadFile = File(...),
    client_ip: str = Depends(verify_ip_whitelist)
):
    file_path = os.path.join(get_version_dir(version), file.filename)
    # Prevent overwriting the template with a data file of the same name
    if file.filename == TEMPLATE_FILENAME:
        return HTMLResponse(content="Cannot upload a data file with the name 'template.xlsx'. Please use the dedicated template upload button.", status_code=400)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # IP 등록
    register_file_owner(version, file.filename, client_ip)

    return RedirectResponse(url="/", status_code=303)


# 마스터 DB 업로드
@router.post("/upload/{version}/masterdb", response_class=RedirectResponse)
async def upload_masterdb(
    version: str,
    file: UploadFile = File(...),
):
    masterdb_dir = os.path.join(get_version_dir(version), "masterdb")
    file_path = os.path.join(masterdb_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/", status_code=303)


@router.get("/download/{version}/{filename:path}", response_class=FileResponse)
async def handle_download(
    version: str,
    filename: str,
    client_ip: str = Depends(verify_ip_whitelist)
):
    file_path = os.path.join(get_version_dir(version), filename)
    if os.path.exists(file_path):
        # 실제 파일명만 추출 (경로 제외)
        actual_filename = os.path.basename(filename)
        return FileResponse(path=file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=actual_filename)
    return HTMLResponse(content="File not found.", status_code=404)



@router.get("/delete/{version}/{filename:path}", response_class=RedirectResponse)
async def handle_delete(
    version: str,
    filename: str,
    client_ip: str = Depends(verify_ip_whitelist)
):
    if ".." in filename or filename.startswith("/"):
        return HTMLResponse(content="Invalid filename.", status_code=400)

    # results 폴더가 아닌 일반 파일의 경우 권한 검증
    if not filename.startswith("results/"):
        if not check_file_owner(version, filename, client_ip):
            return HTMLResponse(content="삭제 권한이 없습니다. 본인이 업로드한 파일만 삭제할 수 있습니다.", status_code=403)

    file_path = os.path.join(get_version_dir(version), filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error deleting file {filename}: {e}")
    return RedirectResponse(url="/", status_code=303)


@router.get("/merge/{version}", response_class=FileResponse)
async def handle_merge(
    version: str,
    client_ip: str = Depends(verify_ip_whitelist)
):
    """
    UPDATED: This endpoint now dynamically finds the header in each data file
    by comparing it to the template's header.
    """
    # template_path는 늘 uploads 폴더 내에 위치시킬 것
    template_path = os.path.join(UPLOADS_DIR, TEMPLATE_FILENAME)
    if version == 'ver1':
        output_filename = "merged_output_"+"r1"+".xlsx"
    else:
        output_filename = "merged_output_"+"r2"+".xlsx"
    output_path = os.path.join(get_version_dir(version), output_filename)

    if not os.path.exists(template_path):
        return HTMLResponse(content=f"Template file '{TEMPLATE_FILENAME}' not found. Please upload it first.", status_code=404)

    # Load the template and get its header
    merged_wb = openpyxl.load_workbook(template_path)
    merged_ws = merged_wb.active

    # 4번째 줄까지는 헤더, 다섯번째 줄 이후부터 합치기 시작
    template_header = [cell.value for cell in merged_ws[4]]
    
    
    files_to_merge = [f for f in os.listdir(get_version_dir(version)) if f.endswith('.xlsx') and f not in [TEMPLATE_FILENAME, output_filename, MASTER_MERGE_FILENAME]]

    for filename in files_to_merge:
        filepath = os.path.join(get_version_dir(version), filename)
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
    

@router.get("/detail", response_class=HTMLResponse)
async def read_about(request: Request):
    return OSError

