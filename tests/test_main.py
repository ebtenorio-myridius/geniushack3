import pytest
from fastapi.testclient import TestClient

from src.app.main import app


@pytest.mark.parametrize(
    ("user", "role", "dashboard"),
    [
        ("product-owner-1", "product_owner", "/intake/product-owner/dashboard/demo"),
        ("analyst-1", "analyst", "/intake/analyst/dashboard/demo"),
        ("committee-1", "committee", "/intake/committee/dashboard/demo"),
    ],
)
def test_root_redirects_logged_in_user_to_role_dashboard(user, role, dashboard):
    client = TestClient(app)
    client.cookies.set("demo_user", user)
    client.cookies.set("demo_role", role)
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == dashboard


@pytest.mark.parametrize(
    "cookies",
    [
        {},
        {"demo_user": "analyst-1"},
        {"demo_user": "unknown-user", "demo_role": "analyst"},
        {"demo_user": "analyst-1", "demo_role": "committee"},
    ],
)
def test_root_redirects_missing_or_invalid_session_to_login(cookies):
    client = TestClient(app)
    for name, value in cookies.items():
        client.cookies.set(name, value)
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/intake/login"


def test_login_page_requires_an_explicit_role_and_has_no_default_user():
    client = TestClient(app)
    response = client.get("/intake/login")

    assert response.status_code == 200
    assert 'name="user" value="" autocomplete="username" required' in response.text
    assert '<option value="" selected disabled>Choose a role</option>' in response.text
    assert '<option value="product_owner" >Product owner</option>' in response.text
    assert "defaultUsers" not in response.text
    assert "userField.value" not in response.text


def test_successful_role_switch_replaces_session_identity():
    client = TestClient(app)
    client.cookies.set("demo_user", "product-owner-1")
    client.cookies.set("demo_role", "product_owner")

    response = client.post(
        "/intake/login",
        data={"user": "analyst-1", "role": "analyst"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/intake/analyst/dashboard/demo"
    assert client.get("/", follow_redirects=False).headers["location"] == "/intake/analyst/dashboard/demo"


def test_switch_role_clears_current_identity_and_routes_root_to_login():
    client = TestClient(app)
    login_response = client.post(
        "/intake/login",
        data={"user": "product-owner-1", "role": "product_owner"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    response = client.get("/intake/switch-role", follow_redirects=True)

    assert response.status_code == 200
    assert response.url.path == "/intake/login"
    assert "demo_user" not in client.cookies
    assert "demo_role" not in client.cookies
    assert client.get("/", follow_redirects=False).headers["location"] == "/intake/login"
    intake_response = client.get("/intake", follow_redirects=False)
    assert intake_response.status_code == 307
    assert intake_response.headers["location"] == "/intake/login"
    assert 'name="user" value="" autocomplete="username" required' in response.text
    assert '<option value="" selected disabled>Choose a role</option>' in response.text


@pytest.mark.parametrize(
    "cookies",
    [
        {},
        {"demo_user": "analyst-1"},
        {"demo_user": "unknown-user", "demo_role": "analyst"},
        {"demo_user": "analyst-1", "demo_role": "committee"},
        {"demo_user": "committee-1", "demo_role": "unknown-role"},
    ],
)
def test_intake_redirects_missing_or_invalid_session_to_login(cookies):
    client = TestClient(app)
    for name, value in cookies.items():
        client.cookies.set(name, value)

    response = client.get("/intake", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/intake/login"


@pytest.mark.parametrize(
    ("user", "role", "dashboard"),
    [
        ("product-owner-1", "product_owner", "/intake/product-owner/dashboard/demo"),
        ("analyst-1", "analyst", "/intake/analyst/dashboard/demo"),
        ("committee-2", "committee", "/intake/committee/dashboard/demo"),
    ],
)
def test_intake_shows_upload_form_for_valid_signed_in_user(user, role, dashboard):
    client = TestClient(app)
    client.cookies.set("demo_user", user)
    client.cookies.set("demo_role", role)

    response = client.get("/intake", follow_redirects=False)

    assert response.status_code == 200
    assert "Submit a change request" in response.text
    assert dashboard in response.text
    if role != "product_owner":
        assert "Product owner dashboard" not in response.text


@pytest.mark.parametrize(
    ("user", "role", "dashboard"),
    [
        ("analyst-1", "analyst", "/intake/analyst/dashboard/demo"),
        ("committee-2", "committee", "/intake/committee/dashboard/demo"),
    ],
)
def test_explicit_non_owner_login_does_not_route_intake_to_product_owner(user, role, dashboard):
    client = TestClient(app)
    response = client.post(
        "/intake/login",
        data={"user": user, "role": role},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == dashboard
    root_response = client.get("/", follow_redirects=False)
    assert root_response.headers["location"] == dashboard
    intake_response = client.get("/intake")
    assert intake_response.status_code == 200
    assert dashboard in intake_response.text