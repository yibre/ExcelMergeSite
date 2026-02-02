from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import json
import os
import openpyxl

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

@router.get("/api/user-agenda")
async def get_user_agenda(request: Request):
    """
    Return user's agenda numbers (union of ver1 and ver2) based on client's IP address.
    """
    # Get client IP address
    client_ip = request.client.host

    # Get user name based on IP
    user_name = get_user_name_by_ip(client_ip)

    try:
        # Load agenda_no.json
        agenda_path = os.path.join(os.path.dirname(__file__), "..", "json", "agenda_no.json")

        if os.path.exists(agenda_path):
            with open(agenda_path, 'r', encoding='utf-8') as f:
                agenda_data = json.load(f)
        else:
            return JSONResponse({
                "user": user_name,
                "agenda_numbers": []
            })

        # Get user's ver1 and ver2 lists
        if user_name in agenda_data:
            ver1 = agenda_data[user_name].get("ver1", [])
            ver2 = agenda_data[user_name].get("ver2", [])

            # Create union of ver1 and ver2, remove duplicates and sort
            agenda_numbers = sorted(list(set(ver1 + ver2)))
        else:
            agenda_numbers = []

        return JSONResponse({
            "user": user_name,
            "agenda_numbers": agenda_numbers
        })

    except Exception as e:
        print(f"Error reading agenda_no.json: {e}")
        return JSONResponse({
            "user": user_name,
            "agenda_numbers": []
        })

def match_agenda_user(filename: str, version: str, file_path: str, keywords: list):
    """
    Check if filename contains any keyword from the keywords list.
    If matched, extract unique values from column B of the Excel file
    and update agenda_no.json with those values.

    Args:
        filename: Name of the uploaded file
        version: Version (ver1 or ver2)
        file_path: Path to the Excel file
        keywords: List of keywords to search in filename (e.g., ["김철수", "이영희"])

    Returns:
        Matched user name if found, None otherwise
    """
    # Check if any keyword exists in filename
    matched_user = None
    for keyword in keywords:
        if keyword in filename:
            matched_user = keyword
            break

    # If no keyword matched, return None
    if matched_user is None:
        return None

    # Read Excel file and extract column B values
    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        # Extract all values from column B (column index 2)
        b_column_values = []
        for row in ws.iter_rows(min_row=1, min_col=2, max_col=2, values_only=True):
            value = row[0]
            # Only add non-None numeric values
            if value is not None:
                try:
                    # Try to convert to integer
                    b_column_values.append(int(value))
                except (ValueError, TypeError):
                    # Skip non-numeric values
                    pass

        wb.close()

        # Remove duplicates by converting to set and back to list
        unique_values = list(set(b_column_values))

        # Update agenda_no.json
        agenda_path = os.path.join(os.path.dirname(__file__), "..", "json", "agenda_no.json")

        # Load current agenda data
        if os.path.exists(agenda_path):
            with open(agenda_path, 'r', encoding='utf-8') as f:
                agenda_data = json.load(f)
        else:
            agenda_data = {}

        # Initialize user entry if not exists
        if matched_user not in agenda_data:
            agenda_data[matched_user] = {"ver1": [], "ver2": []}

        # Update the specific version list with unique values
        agenda_data[matched_user][version] = unique_values

        # Save updated agenda data
        with open(agenda_path, 'w', encoding='utf-8') as f:
            json.dump(agenda_data, f, indent=4, ensure_ascii=False)

        return matched_user

    except Exception as e:
        print(f"Error in match_agenda_user: {e}")
        return None