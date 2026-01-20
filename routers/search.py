import os
import openpyxl
from fastapi import Request, APIRouter, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from routers.authentification import verify_ip_whitelist

# --- Configuration ---
UPLOADS_DIR = "uploads"
VERSIONS = ["ver1", "ver2"]

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_version_dir(version: str):
    """Helper to get the correct versioned directory path."""
    return os.path.join(UPLOADS_DIR, version)


def search_key_in_excel(version: str, key_value: str) -> list[dict]:
    """
    업로드된 엑셀 파일의 두 번째 열(B열)에서 key_value와 일치하는 모든 행 찾기

    Args:
        version (str): 버전 디렉토리 (ver1 또는 ver2)
        key_value (str): 검색할 키 값.

    Returns:
        List[dict]: 키 값과 일치하는 모든 행의 데이터와 스타일 정보.
                    각 딕셔너리는 'cells' (셀 값 리스트)와 'styles' (스타일 리스트)를 포함.
    """
    matching_rows = []
    try:
        # version/results 디렉토리에서 'result'로 시작하는 파일 찾기
        version_dir = get_version_dir(version)
        results_dir = os.path.join(version_dir, "results")
        master_files = [f for f in os.listdir(results_dir) if f.startswith('result') and f.endswith('.xlsx')]

        if not master_files:
            raise HTTPException(status_code=404, detail=f"'{version}/results' 디렉토리에서 'result'로 시작하는 파일을 찾을 수 없습니다.")

        # 가장 최근 파일 사용 (파일명 기준 정렬)
        master_file = sorted(master_files)[-1]
        master_path = os.path.join(results_dir, master_file)

        workbook = openpyxl.load_workbook(master_path)
        sheet = workbook.active

        # 옵션 1. 데이터 셀 색은 빼고 데이터만 추출하기 (현재 사용 중)
        for row in sheet.iter_rows(min_row=5, values_only=True):
            # 행에 데이터가 있고, 다섯 번째 열이 존재하는지 확인
            if len(row) > 1 and row[1] is not None:
                # 다섯 번째 열(인덱스 1)의 값을 문자열로 변환하여 비교
                if str(row[1]).strip() == str(key_value).strip():
                    # 빈 셀(None)은 빈 문자열로 변환하여 추가
                    clean_row = ["" if cell is None else cell for cell in row]
                    matching_rows.append(clean_row)

    except Exception as e:
        # 파일 처리 중 오류 발생 시 예외 처리
        raise HTTPException(status_code=400, detail=f"'master' 파일 처리 중 오류 발생: {e}")

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

    return "".join(styles)


@router.get("/search/", summary="key로 행 값 검색", response_class=HTMLResponse)
async def search_rows_by_key(
    request: Request,
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
    # 각 파일에 대해 검색 함수 호출, 에러 발생 시 빈 리스트 반환
    try:
        r1_data = search_key_in_excel("ver1", key)
    except HTTPException:
        r1_data = []

    try:
        r2_data = search_key_in_excel("ver2", key)
    except HTTPException:
        r2_data = []

    context = {
        "request": request,
        "key": key,
        "data": [['ver1', r1_data], ['ver2', r2_data]]
    }

    return templates.TemplateResponse("search.html", context)