from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import json
import os

router = APIRouter()

def get_user_name_by_ip(ip: str) -> str:
    """
    Get user name from user_data.json based on IP address.
    """
    try:
        user_data_path = os.path.join(os.path.dirname(__file__), "..", "json", "user_data.json")
        with open(user_data_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # Return user name for IP, default to "Guest" if not found
        return user_data.get(ip, "Guest")
    except Exception as e:
        print(f"Error reading user_data.json: {e}")
        return "Guest"

@router.get("/api/user-info")
async def get_user_info(request: Request):
    """
    Return user information based on client's IP address.
    """
    # Get client IP address
    client_ip = request.client.host

    # Get user name based on IP
    user_name = get_user_name_by_ip(client_ip)

    return JSONResponse({
        "ip": client_ip,
        "name": user_name
    })
