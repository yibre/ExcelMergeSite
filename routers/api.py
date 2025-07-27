import os
import shutil
import openpyxl
from fastapi import Request, UploadFile, File, APIRouter, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# --- Configuration ---
UPLOADS_DIR = "uploads"
TEMPLATE_FILENAME = "template.xlsx"
MASTER_MERGE_FILENAME = "master.xlsx"
VERSIONS = ["ver1", "ver2"]

os.makedirs(UPLOADS_DIR, exist_ok=True)
for version in VERSIONS:
    os.makedirs(os.path.join(UPLOADS_DIR, version), exist_ok=True)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")

# 검색 결과 global 함수화


@router.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    """
    This endpoint serves the home page.
    It now separates the template file from the data files for display.
    """
    try:
        all_files = os.listdir(UPLOADS_DIR)
        files1 = os.listdir(UPLOADS_DIR+"/ver1")
        files2 = os.listdir(UPLOADS_DIR+"/ver2")
        template_file = TEMPLATE_FILENAME if TEMPLATE_FILENAME in files1 else None
        data_files = [f for f in files1 if f != TEMPLATE_FILENAME]
    except OSError:
        print("os error occured")
        template_file = None
        data_files = []
        
    context = {
        "request": request,
        "title": "Home Page - File Uploader",
        "message": "Upload data files below. Use the dedicated button for the template.",
        "template_file": template_file,
        "data_files": data_files,
        "master_merge_filename": MASTER_MERGE_FILENAME
    }
    return templates.TemplateResponse("home.html", context)


@router.post("/upload_template", response_class=RedirectResponse)
async def handle_upload_template(file: UploadFile = File(...)):
    """
    NEW: Dedicated endpoint for uploading the template.xlsx file.
    It will always be saved as 'template.xlsx'.
    """
    file_path = os.path.join(UPLOADS_DIR, TEMPLATE_FILENAME)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/", status_code=303)


@router.post("/upload", response_class=RedirectResponse)
async def handle_upload(file: UploadFile = File(...)):
    """
    This endpoint handles the data file uploads.
    """
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    # Prevent overwriting the template with a data file of the same name
    if file.filename == TEMPLATE_FILENAME:
        return HTMLResponse(content="Cannot upload a data file with the name 'template.xlsx'. Please use the dedicated template upload button.", status_code=400)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/", status_code=303)



@router.get("/download/{filename}", response_class=FileResponse)
async def handle_download(filename: str):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, media_type='routerlication/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=filename)
    return HTMLResponse(content="File not found.", status_code=404)



@router.get("/delete/{filename}", response_class=RedirectResponse)
async def handle_delete(filename: str):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if ".." in filename or filename.startswith("/"):
        return HTMLResponse(content="Invalid filename.", status_code=400)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error deleting file {filename}: {e}")
    return RedirectResponse(url="/", status_code=303)



@router.get("/merge", response_class=FileResponse)
async def handle_merge():
    """
    UPDATED: This endpoint now dynamically finds the header in each data file
    by comparing it to the template's header.
    """
    template_path = os.path.join(UPLOADS_DIR, TEMPLATE_FILENAME)
    output_filename = "merged_output.xlsx"
    output_path = os.path.join(UPLOADS_DIR, output_filename)

    if not os.path.exists(template_path):
        return HTMLResponse(content=f"Template file '{TEMPLATE_FILENAME}' not found. Please upload it first.", status_code=404)

    # Load the template and get its header
    merged_wb = openpyxl.load_workbook(template_path)
    merged_ws = merged_wb.active
    template_header = [cell.value for cell in merged_ws[4]]
    
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


## 현재 안 쓰는 코드
@router.get("/download_my_data/{original_filename}")
async def download_my_data(original_filename: str):
    master_path = os.path.join(UPLOADS_DIR, MASTER_MERGE_FILENAME)
    user_file_path = os.path.join(UPLOADS_DIR, original_filename)

    if not os.path.exists(master_path):
        return HTMLResponse(content=f"Master file '{MASTER_MERGE_FILENAME}' not found. Please upload it.", status_code=404)
    if not os.path.exists(user_file_path):
        return HTMLResponse(content=f"Original user file '{original_filename}' not found.", status_code=404)

    try:
        user_wb = openpyxl.load_workbook(user_file_path)
        user_ws = user_wb.active
        key_value = user_ws['B5'].value
        if key_value is None:
            return HTMLResponse(content=f"Could not find a key value in cell B6 of '{original_filename}'.", status_code=400)

        filtered_wb = openpyxl.Workbook()
        filtered_ws = filtered_wb.active
        
        master_wb = openpyxl.load_workbook(master_path)
        master_ws = master_wb.active
        header = [cell.value for cell in master_ws[4]]
        filtered_ws.append(header)

        for row in master_ws.iter_rows(min_row=2, values_only=True):
            print(row)
            if len(row) > 1 and row[1] == key_value:
                filtered_ws.append(row)
        
        output_filename = f"filtered_for_{key_value}.xlsx"
        output_path = os.path.join(UPLOADS_DIR, output_filename)
        filtered_wb.save(output_path)

        return FileResponse(path=output_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=output_filename)

    except Exception as e:
        print(f"An error occurred: {e}")
        return HTMLResponse(content=f"An error occurred during processing: {e}", status_code=500)
    

def search_key_in_excel(key_value: str) -> list[list[any]]:
    """
    업로드된 엑셀 파일의 두 번째 열(B열)에서 key_value와 일치하는 모든 행 찾기

    Args:
        file (UploadFile): 사용자가 업로드한 엑셀 파일. file: UploadFile,
        key_value (str): 검색할 키 값.

    Returns:
        List[List[Any]]: 키 값과 일치하는 모든 행의 데이터 리스트.
    """
    matching_rows = []
    try:
        # 업로드된 파일을 메모리에서 직접 로드
        # workbook = openpyxl.load_workbook(file.file)
        master_path = os.path.join(UPLOADS_DIR, "merged_output.xlsx")
        workbook = openpyxl.load_workbook(master_path)
        sheet = workbook.active

        # 헤더를 제외하고 두 번째 행부터 순회
        # values_only=True로 설정하면 셀 객체가 아닌 값의 튜플을 바로 얻을 수 있어 편리합니다.
        for row in sheet.iter_rows(min_row=6, values_only=True):
            # 행에 데이터가 있고, 두 번째 열이 존재하는지 확인
            if len(row) > 1 and row[1] is not None:
                # 두 번째 열(인덱스 1)의 값을 문자열로 변환하여 비교
                if str(row[1]).strip() == str(key_value).strip():
                    # 빈 셀(None)은 빈 문자열로 변환하여 추가
                    clean_row = ["" if cell is None else cell for cell in row]
                    matching_rows.append(clean_row)

    except Exception as e:
        # 파일 처리 중 오류 발생 시 예외 처리
        raise HTTPException(status_code=400, detail=f"'{file.filename}' 파일 처리 중 오류 발생: {e}")

    return matching_rows


def get_cell_styles(cell):
    """
    셀 객체에서 CSS 스타일 추출
    """
    styles=[]
    if cell.fill.fgColor.rgb:
        #openpyxl의 ARGB 형식에서 RGB만 추출해 CSS hex 코드로 변환
        bg_color = f"#{cell.fill.fgColor.rgb[2:]}" if len(cell.fill.fgColor.rgb) == 8 else f"#{cell.fill.fgColor.rgb}"
        styles.append(f"background-color: {bg_color};")

    return " ".json(styles)


@router.get("/search/", summary="key로 행 값 검색", response_class=HTMLResponse)
async def search_rows_by_key(
    key: int = Query(..., description="The integer value to search for")
    ):
    """
    두 개의 엑셀 파일을 업로드받아, 각 파일의 **두 번째 열**에서 주어진 `key` 값과
    일치하는 모든 행을 찾아 반환합니다.

    - **key**: 검색할 값 (예: 14)
    - **file1**: 검색 대상 첫 번째 엑셀 파일
    - **file2**: 검색 대상 두 번째 엑셀 파일
    file1: UploadFile = File(..., description="첫 번째 엑셀 파일 (.xlsx)"),
    file2: UploadFile = File(..., description="두 번째 엑셀 파일 (.xlsx)")
    """
    # 각 파일에 대해 검색 함수 호출
    # results_from_file1 = search_key_in_excel(file1, key)
    results_from_file2 = search_key_in_excel(key)
    print(results_from_file2)

    context = {
        "key": key,
        "hi": "hithere",
    }

    return templates.TemplateResponse("search.html", context)


@router.get("/about", response_class=HTMLResponse)
async def read_about(request: Request):
    context = {
        "request": request,
        "title": "About Us",
        "description": "This is a page explaining what our site is about."
    }
    return templates.TemplateResponse("about.html", context)
