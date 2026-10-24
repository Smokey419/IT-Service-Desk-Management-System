
import pytest
from flask import template_rendered
from werkzeug.security import generate_password_hash

from app import app, db, User, Ticket, Asset


@pytest.fixture
def client(tmp_path):
    # Use a separate temporary SQLite database.
    test_database = tmp_path / "test_servicedesk.db"

    original_config = {
        "TESTING": app.config["TESTING"],
        "SECRET_KEY": app.config["SECRET_KEY"],
        "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
    }

    app.config.update(
        TESTING=True,
        SECRET_KEY="temporary-pytest-secret",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{test_database.as_posix()}",
    )

    try:
        with app.app_context():
            db.create_all()

            admin = User(
                username="testadmin",
                password_hash=generate_password_hash("TestAdmin123!"),
                role="admin",
            )

            employee = User(
                username="testemployee",
                password_hash=generate_password_hash("TestEmployee123!"),
                role="employee",
            )

            other_employee = User(
                username="otheremployee",
                password_hash=generate_password_hash("OtherEmployee123!"),
                role="employee",
            )

            db.session.add_all([admin, employee, other_employee])
            db.session.commit()

            ticket = Ticket(
                title="Cisco VPN connection issue",
                description="Unable to connect to the company VPN.",
                category="Network / VPN",
                priority="High",
                status="Open",
                created_by=employee.id,
            )

            db.session.add(ticket)
            db.session.commit()

        with app.test_client() as test_client:
            yield test_client

    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()

        app.config.update(original_config)


def login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_login_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code in (302, 401)


def test_invalid_login(client):
    response = client.post(
        "/login",
        data={
            "username": "testadmin",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


def test_admin_login(client):
    response = login(client, "testadmin", "TestAdmin123!")
    assert response.status_code == 200
    assert b"testadmin" in response.data


def test_employee_can_view_own_ticket(client):
    login(client, "testemployee", "TestEmployee123!")

    response = client.get("/tickets/1")

    assert response.status_code == 200
    assert b"Cisco VPN connection issue" in response.data


def test_employee_cannot_view_another_users_ticket(client):
    login(client, "otheremployee", "OtherEmployee123!")

    response = client.get("/tickets/1")

    assert response.status_code == 403


def test_employee_cannot_access_assets(client):
    login(client, "testemployee", "TestEmployee123!")

    response = client.get("/assets")

    assert response.status_code == 403


def test_admin_can_access_assets(client):
    login(client, "testadmin", "TestAdmin123!")

    response = client.get("/assets")

    assert response.status_code == 200


def test_employee_cannot_update_ticket(client):
    login(client, "testemployee", "TestEmployee123!")

    response = client.post(
        "/tickets/1/update",
        data={
            "status": "Resolved",
            "priority": "Low",
            "assigned_to": "",
            "resolution_notes": "Unauthorized update attempt",
        },
    )

    assert response.status_code == 403

    with app.app_context():
        ticket = db.session.get(Ticket, 1)
        assert ticket.status == "Open"


def test_admin_can_search_tickets(client):
    login(client, "testadmin", "TestAdmin123!")

    response = client.get("/tickets/search?search=Cisco")

    assert response.status_code == 200
    assert b"Cisco VPN connection issue" in response.data


def test_search_returns_no_matches(client):
    login(client, "testadmin", "TestAdmin123!")

    response = client.get("/tickets/search?search=NonexistentIssue")

    assert response.status_code == 200
    assert b"No tickets match" in response.data


def test_employee_can_create_ticket(client):
    login(client, "testemployee", "TestEmployee123!")

    response = client.post(
        "/tickets/new",
        data={
            "title": "Outlook will not open",
            "description": "Outlook crashes during startup.",
            "category": "Email",
            "priority": "Medium",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        ticket = Ticket.query.filter_by(
            title="Outlook will not open"
        ).first()

        assert ticket is not None
        assert ticket.status == "Open"
        assert ticket.requester.username == "testemployee"
