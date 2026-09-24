from fastapi import Header, HTTPException

from src.app.models.schemas import UserRole

DEMO_USER_ROLES = {
    "product-owner-1": UserRole.product_owner,
    "analyst-1": UserRole.analyst,
    "committee-1": UserRole.committee,
    "committee-2": UserRole.committee,
    "committee-3": UserRole.committee,
}


def validate_demo_login(user: str, role: UserRole) -> bool:
    return DEMO_USER_ROLES.get(user.strip()) == role


def require_role(role: UserRole, demo_user: str | None, demo_role: str | None) -> str:
    if (
        not demo_user
        or demo_role != role.value
        or DEMO_USER_ROLES.get(demo_user) != role
    ):
        raise HTTPException(status_code=403, detail=f"A {role.value} role is required")
    return demo_user