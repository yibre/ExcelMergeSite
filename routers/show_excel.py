from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io

router = APIRouter("/detail")
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")

@router.post("/", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(io.BytesIO(contents), sheet_name=None)
        
        # 모든 시트의 데이터를 딕셔너리로 저장
        sheets_data = {}
        for sheet_name, sheet_df in df.items():
            # NaN 값을 빈 문자열로 변환
            sheet_df = sheet_df.fillna('')
            
            # 데이터프레임을 HTML 테이블로 변환 (헤더 포함)
            sheets_data[sheet_name] = {
                'columns': sheet_df.columns.tolist(),
                'data': sheet_df.values.tolist()
            }
        
        return templates.TemplateResponse(
            "about.html", 
            {
                "request": request, 
                "sheets_data": sheets_data,
                "filename": file.filename
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e)
            }
        )
