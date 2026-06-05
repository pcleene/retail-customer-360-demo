"""JWT middleware extracting role from Bearer token, injecting request.state.rbac_filter."""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.auth.jwt_utils import decode_token, get_rbac_filter

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Extract user info from JWT. Returns internal_staff if no token."""
    if not credentials:
        return {
            "user_id": "anonymous",
            "role": "internal_staff",
            "name": "Anonymous",
            "rbac_filter": {},
        }
    try:
        payload = decode_token(credentials.credentials)
        role = payload.get("role", "internal_staff")
        supplier_id = payload.get("supplier_id")
        rbac_filter = get_rbac_filter(role, supplier_id)
        return {
            "user_id": payload.get("user_id", "unknown"),
            "role": role,
            "name": payload.get("name", "Unknown"),
            "supplier_id": supplier_id,
            "rbac_filter": rbac_filter,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
