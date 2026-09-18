from fastapi import Header, HTTPException

from src.app.models.schemas import UserRole


def require_role(role: UserRole, demo_user: str | None, demo_role: str | None) -> str:
    if not demo_user or demo_role != role.value:
        raise HTTPException(status_code=403, detail=f"A {role.value} role is required")
    return demo_user