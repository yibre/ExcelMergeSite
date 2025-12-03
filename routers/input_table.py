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

