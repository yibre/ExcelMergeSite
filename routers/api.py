from fastapi import APIRouter

router = APIRouter()

@router.get("/files")
def get_files():
    return {"hi":"are you there?"}