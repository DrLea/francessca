"""Landing-page endpoints: public lawyer preview, lawyer sign-up, plans."""
from __future__ import annotations

from app.seeds.lawyers import sample_lawyers
from app.services.lawyer_service import LawyerService

APPLICATION = {
    "name": "Dr. Mara Lenz",
    "email": "Mara@Lenz-Recht.de",
    "law_firm": "Lenz Recht",
    "city": "München",
    "phone": "+49 89 111111",
    "specializations": ["Employment", "  Immigration  ", ""],
    "languages": ["German", "English"],
    "message": "I would like to be listed.",
}


def _register(client, email="user@example.com", **extra):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test", **extra},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _admin_token(client, db_session):
    from app.models.user import User, UserRole

    token = _register(client, email="admin@example.com")
    user = db_session.query(User).filter(User.email == "admin@example.com").one()
    user.role = UserRole.admin
    db_session.commit()
    return token


def test_public_preview_hides_contact_details(client, db_session):
    LawyerService(db_session).sync_from_parsed(sample_lawyers())
    db_session.commit()

    resp = client.get("/public/lawyers?limit=3")
    assert resp.status_code == 200  # no auth header at all
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 3
    first = body["items"][0]
    assert first["name"]
    assert "email" not in first and "phone" not in first


def test_lawyer_application_is_pending_until_an_admin_approves(client, db_session):
    created = client.post("/public/lawyer-applications", json=APPLICATION)
    assert created.status_code == 201, created.text
    application = created.json()
    assert application["status"] == "pending"
    assert application["email"] == "mara@lenz-recht.de"  # normalised
    assert application["specializations"] == ["Employment", "Immigration"]

    # Nothing is published yet.
    assert client.get("/public/lawyers").json()["total"] == 0

    token = _admin_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}
    pending = client.get(
        "/admin/lawyer-applications?status_filter=pending", headers=headers
    ).json()
    assert [a["id"] for a in pending] == [application["id"]]

    approved = client.post(
        f"/admin/lawyer-applications/{application['id']}/approve", headers=headers
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["lawyer_id"]

    listed = client.get("/public/lawyers").json()
    assert [item["name"] for item in listed["items"]] == ["Dr. Mara Lenz"]
    assert listed["items"][0]["specializations"] == ["Employment", "Immigration"]

    # Reviewing it twice is a conflict, not a second directory entry.
    again = client.post(
        f"/admin/lawyer-applications/{application['id']}/approve", headers=headers
    )
    assert again.status_code == 409


def test_rejected_applications_never_reach_the_directory(client, db_session):
    application = client.post("/public/lawyer-applications", json=APPLICATION).json()
    headers = {"Authorization": f"Bearer {_admin_token(client, db_session)}"}
    rejected = client.post(
        f"/admin/lawyer-applications/{application['id']}/reject", headers=headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert client.get("/public/lawyers").json()["total"] == 0


def test_application_requires_a_real_email(client):
    bad = client.post(
        "/public/lawyer-applications", json={"name": "X Y", "email": "not-an-email"}
    )
    assert bad.status_code == 422


def test_plan_switch_is_free_during_beta(client):
    token = _register(client, email="plan@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/me", headers=headers).json()["tier"] == "free"

    upgraded = client.post("/me/plan", headers=headers, json={"tier": "premium"})
    assert upgraded.status_code == 200, upgraded.text
    assert upgraded.json()["tier"] == "premium"
    assert upgraded.json()["token_limit"] is None  # unlimited

    back = client.post("/me/plan", headers=headers, json={"tier": "free"})
    assert back.json()["tier"] == "free"
    assert back.json()["token_limit"] == 100_000


def test_plan_switch_requires_a_login(client):
    assert client.post("/me/plan", json={"tier": "premium"}).status_code == 401
