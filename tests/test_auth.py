import pytest
from fastapi import HTTPException

from src.app.models.schemas import UserRole
from src.app.services.auth import require_role, validate_demo_login


def test_demo_users_are_bound_to_their_roles():
    assert validate_demo_login("analyst-1", UserRole.analyst)
    assert validate_demo_login("committee-1", UserRole.committee)
    assert not validate_demo_login("analyst-1", UserRole.committee)
    assert not validate_demo_login("committee-1", UserRole.analyst)
    assert not validate_demo_login("unknown-user", UserRole.analyst)


def test_require_role_rejects_mismatched_demo_identity():
    with pytest.raises(HTTPException) as error:
        require_role(UserRole.committee, "analyst-1", "committee")

    assert error.value.status_code == 403
