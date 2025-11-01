import json
import os
from fastapi import Request, HTTPException, status
from typing import Optional


def load_allowed_ips() -> list[str]:
    """
    json/ip.json 파일에서 허용된 IP 목록을 로드합니다.

    Returns:
        list[str]: 허용된 IP 주소 리스트
    """
    json_path = os.path.join(os.path.dirname(__file__), "..", "json", "ip.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("allowed_ips", [])
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IP 설정 파일을 찾을 수 없습니다."
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IP 설정 파일 형식이 올바르지 않습니다."
        )


def get_client_ip(request: Request) -> str:
    """
    클라이언트의 실제 IP 주소를 추출합니다.
    프록시나 로드밸런서를 통해 들어온 경우 X-Forwarded-For 헤더를 확인합니다.

    Args:
        request (Request): FastAPI Request 객체

    Returns:
        str: 클라이언트 IP 주소
    """
    # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 뒤에 있는 경우)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For는 여러 IP가 콤마로 구분될 수 있음 (첫 번째가 실제 클라이언트 IP)
        return forwarded_for.split(",")[0].strip()

    # X-Real-IP 헤더 확인
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 직접 연결된 경우 client.host 사용
    if request.client:
        return request.client.host

    return "unknown"


async def verify_ip_whitelist(request: Request) -> str:
    """
    요청한 클라이언트의 IP가 허용 목록에 있는지 확인합니다.
    FastAPI의 Depends()로 사용할 수 있는 의존성 함수입니다.

    Args:
        request (Request): FastAPI Request 객체

    Returns:
        str: 인증된 클라이언트 IP 주소

    Raises:
        HTTPException: IP가 허용 목록에 없는 경우 403 에러
    """
    client_ip = get_client_ip(request)
    allowed_ips = load_allowed_ips()

    if client_ip not in allowed_ips:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"접근이 거부되었습니다. IP 주소 '{client_ip}'는 허용되지 않습니다."
        )

    return client_ip

