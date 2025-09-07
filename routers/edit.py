from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
from pathlib import Path
import openpyxl
from io import BytesIO
import base64
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/edit")
templates = Jinja2Templates(directory="templates")

# 데이터 모델 정의
class TableData(BaseModel):
    headers: List[str]
    rows: List[List[Any]]

class DataSubmission(BaseModel):
    data: TableData 