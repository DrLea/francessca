"""Lawyer accounts, orders, the free allowance, feedback, reviews, admin."""
from __future__ import annotations

from app.models.case import Case
from app.models.user import User, UserRole
from app.services.lead_quality import score_lead

LAWYER = {
    "email": "Mara@Lenz-Recht.de",
    "password": "password123",
    "name": "Dr. Mara Lenz",
    "city": "München",
    "specializations": ["Employment", "employment", " Immigration "],
    "languages": ["German", "English"],
}

SUMMARY = {
    "case_type": "employment",
    "narrative": "I was dismissed without notice. " * 30,
    "timeline": ["hired 2021", "warning in May", "dismissed in June", "letter in July"],
    "people_involved": ["employer", "HR manager"],
    "important_dates": ["2026-06-01", "2026-06-22"],
    "documents_available": ["contract", "dismissal letter", "payslips"],
    "questions_for_lawyer": ["Is the notice period valid?", "Can I claim severance?"],
}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _client(client, email="client@example.com") -> str:
    resp = client.post(
        "/auth/register", json={"email": email, "password": "password123", "full_name": "Cli Ent"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _admin(client, db_session) -> str:
    token = _client(client, "admin@example.com")
    db_session.query(User).filter(User.email == "admin@example.com").one().role = UserRole.admin
    db_session.commit()
    return token


def _lawyer(client, **extra) -> str:
    resp = client.post("/auth/register-lawyer", json={**LAWYER, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _approved_lawyer(client, admin: str, **extra) -> tuple[str, int]:
    token = _lawyer(client, **extra)
    lawyer_id = client.get("/lawyer/me", headers=_auth(token)).json()["profile"]["id"]
    pending = client.get(
        "/admin/lawyer-applications?status_filter=pending", headers=_auth(admin)
    ).json()
    application = next(a for a in pending if a["lawyer_id"] == lawyer_id)
    resp = client.post(
        f"/admin/lawyer-applications/{application['id']}/approve", headers=_auth(admin)
    )
    assert resp.status_code == 200, resp.text
    return token, lawyer_id


def _case(db_session, email="client@example.com") -> int:
    user = db_session.query(User).filter(User.email == email).one()
    case = Case(user_id=user.id, title="Dismissal", case_type="employment", summary=SUMMARY)
    db_session.add(case)
    db_session.commit()
    return case.id


def test_lawyer_registers_but_is_hidden_until_approved(client, db_session):
    admin = _admin(client, db_session)
    token = _lawyer(client)

    me = client.get("/lawyer/me", headers=_auth(token)).json()
    assert me["approval"] == "pending"
    assert me["profile"]["is_published"] is False
    assert me["profile"]["email"] == "mara@lenz-recht.de"
    assert me["profile"]["specializations"] == ["Employment", "Immigration"]  # de-duplicated
    assert me["quota"] == {
        "free_total": 3, "extra": 0, "used": 0, "remaining": 3,
        "free_remaining": 3, "contact_email": None,
    }
    assert client.get("/auth/me", headers=_auth(token)).json()["role"] == "lawyer"

    # Not in the directory, signed in or not.
    client_token = _client(client)
    found = client.get("/lawyers/search?city=München", headers=_auth(client_token)).json()
    assert all(item["name"] != "Dr. Mara Lenz" for item in found["items"])
    assert client.get("/public/lawyers").json()["total"] == 0

    pending = client.get("/admin/lawyer-applications", headers=_auth(admin)).json()
    assert pending[0]["user_id"] is not None
    assert client.post(
        f"/admin/lawyer-applications/{pending[0]['id']}/approve", headers=_auth(admin)
    ).status_code == 200

    assert client.get("/lawyer/me", headers=_auth(token)).json()["approval"] == "approved"
    found = client.get("/lawyers/search?city=München", headers=_auth(client_token)).json()
    assert found["items"][0]["name"] == "Dr. Mara Lenz"
    assert found["items"][0]["accepts_requests"] is True


def test_portal_is_for_lawyers_only(client):
    token = _client(client)
    assert client.get("/lawyer/me", headers=_auth(token)).status_code == 403
    assert client.get("/lawyer/orders", headers=_auth(token)).status_code == 403
    assert client.get("/admin/overview", headers=_auth(token)).status_code == 403
    assert client.get("/lawyer/me").status_code == 401


def test_profile_edit(client):
    token = _lawyer(client)
    resp = client.put(
        "/lawyer/profile",
        headers=_auth(token),
        json={
            "bio": "Twenty years of employment law.",
            "years_experience": 20,
            "website": "https://lenz-recht.de",
            "languages": ["German", "Turkish"],
            "specializations": ["Family"],
            "phone": "",
        },
    )
    assert resp.status_code == 200, resp.text
    profile = resp.json()["profile"]
    assert profile["bio"].startswith("Twenty")
    assert profile["languages"] == ["German", "Turkish"]
    assert profile["specializations"] == ["Family"]
    assert profile["phone"] is None
    assert resp.json()["profile_completeness"] > 40

    # Saving again with an overlapping list must not trip the unique
    # (lawyer_id, name) constraint — the form always resends every field.
    again = client.put(
        "/lawyer/profile",
        headers=_auth(token),
        json={"specializations": ["Family", "Employment"]},
    )
    assert again.status_code == 200, again.text
    assert sorted(again.json()["profile"]["specializations"]) == ["Employment", "Family"]

    bad = client.put(
        "/lawyer/profile", headers=_auth(token), json={"website": "javascript:alert(1)"}
    )
    assert bad.status_code == 422


def test_order_flow_hides_contact_until_accepted(client, db_session):
    admin = _admin(client, db_session)
    lawyer, lawyer_id = _approved_lawyer(client, admin)
    customer = _client(client)
    case_id = _case(db_session)

    sent = client.post(
        "/orders",
        headers=_auth(customer),
        json={"lawyer_id": lawyer_id, "case_id": case_id, "message": "Please help. " * 12},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["status"] == "pending"
    assert sent.json()["quality_score"] >= 80

    # A second request to the same lawyer while one is waiting is refused.
    again = client.post(
        "/orders", headers=_auth(customer), json={"lawyer_id": lawyer_id, "message": "hello?"}
    )
    assert again.status_code == 409

    orders = client.get("/lawyer/orders", headers=_auth(lawyer)).json()
    assert len(orders) == 1
    order = orders[0]
    assert order["client"] is None  # not revealed yet
    assert order["case_summary"]["case_type"] == "employment"
    assert order["quality_breakdown"]["documents"] == 20

    accepted = client.post(f"/lawyer/orders/{order['id']}/accept", headers=_auth(lawyer))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["client"]["email"] == "client@example.com"
    assert accepted.json()["is_free"] is True
    assert client.get("/lawyer/me", headers=_auth(lawyer)).json()["quota"]["remaining"] == 2

    # No review before the order is closed.
    early = client.post(
        f"/orders/{order['id']}/review", headers=_auth(customer), json={"rating": 5}
    )
    assert early.status_code == 409

    closed = client.post(
        f"/lawyer/orders/{order['id']}/close",
        headers=_auth(lawyer),
        json={"outcome": "won", "deal_value": 1500},
    )
    assert closed.json()["status"] == "closed_won"

    reviewed = client.post(
        f"/orders/{order['id']}/review",
        headers=_auth(customer),
        json={"rating": 4, "comment": "Clear and fast."},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["review"]["rating"] == 4
    assert reviewed.json()["can_review"] is False
    assert client.post(
        f"/orders/{order['id']}/review", headers=_auth(customer), json={"rating": 1}
    ).status_code == 409

    stats = client.get("/lawyer/stats", headers=_auth(lawyer)).json()
    assert stats["orders"]["won"] == 1
    assert stats["rates"]["win"] == 1.0
    assert stats["finance"]["revenue"] == 1500.0
    assert stats["finance"]["free_orders_used"] == 1
    assert stats["rating"] == {"average": 4.0, "count": 1}
    assert len(stats["monthly"]) == 6 and stats["monthly"][-1]["revenue"] == 1500.0

    listed = client.get("/lawyers/search", headers=_auth(customer)).json()["items"][0]
    assert listed["rating_avg"] == 4.0 and listed["rating_count"] == 1


def test_orders_are_private_to_their_lawyer_and_client(client, db_session):
    admin = _admin(client, db_session)
    lawyer, lawyer_id = _approved_lawyer(client, admin)
    other_lawyer, _ = _approved_lawyer(client, admin, email="other@law.de", name="Otto Other")
    customer = _client(client)
    stranger = _client(client, "stranger@example.com")
    order_id = client.post(
        "/orders", headers=_auth(customer), json={"lawyer_id": lawyer_id, "message": "Hello"}
    ).json()["id"]

    assert client.get("/lawyer/orders", headers=_auth(other_lawyer)).json() == []
    assert client.post(
        f"/lawyer/orders/{order_id}/accept", headers=_auth(other_lawyer)
    ).status_code == 404
    assert client.post(f"/orders/{order_id}/cancel", headers=_auth(stranger)).status_code == 404
    # Someone else's case cannot be attached.
    case_id = _case(db_session)
    assert client.post(
        "/orders", headers=_auth(stranger), json={"lawyer_id": lawyer_id, "case_id": case_id}
    ).status_code == 404
    # Lawyers do not send cases.
    assert client.post(
        "/orders", headers=_auth(other_lawyer), json={"lawyer_id": lawyer_id, "message": "x"}
    ).status_code == 403

    assert client.post(f"/orders/{order_id}/cancel", headers=_auth(customer)).status_code == 200
    assert client.get("/lawyer/orders", headers=_auth(lawyer)).json() == []


def test_free_allowance_then_admin_unlock(client, db_session):
    admin = _admin(client, db_session)
    lawyer, lawyer_id = _approved_lawyer(client, admin)

    ids = []
    for i in range(4):
        token = _client(client, f"c{i}@example.com")
        ids.append(
            client.post(
                "/orders", headers=_auth(token), json={"lawyer_id": lawyer_id, "message": "Hi"}
            ).json()["id"]
        )
    for order_id in ids[:3]:
        assert client.post(
            f"/lawyer/orders/{order_id}/accept", headers=_auth(lawyer)
        ).status_code == 200
    # Declining never costs anything; the fourth acceptance hits the paywall.
    blocked = client.post(f"/lawyer/orders/{ids[3]}/accept", headers=_auth(lawyer))
    assert blocked.status_code == 402
    assert client.get("/lawyer/me", headers=_auth(lawyer)).json()["quota"]["remaining"] == 0

    accounts = client.get("/admin/lawyer-accounts", headers=_auth(admin)).json()
    assert accounts[0]["orders_used"] == 3 and accounts[0]["orders_remaining"] == 0
    unlocked = client.patch(
        f"/admin/lawyer-accounts/{lawyer_id}", headers=_auth(admin), json={"extra_orders": 5}
    )
    assert unlocked.json()["orders_remaining"] == 5

    paid = client.post(f"/lawyer/orders/{ids[3]}/accept", headers=_auth(lawyer))
    assert paid.status_code == 200
    assert paid.json()["is_free"] is False
    finance = client.get("/lawyer/stats", headers=_auth(lawyer)).json()["finance"]
    assert finance["free_orders_used"] == 3 and finance["paid_orders_used"] == 1


def test_feedback_reaches_the_admin(client, db_session):
    admin = _admin(client, db_session)
    lawyer, lawyer_id = _approved_lawyer(client, admin)
    customer = _client(client)
    order_id = client.post(
        "/orders", headers=_auth(customer), json={"lawyer_id": lawyer_id, "message": "Hi"}
    ).json()["id"]

    created = client.post(
        "/lawyer/feedback",
        headers=_auth(lawyer),
        json={"category": "lead_quality", "rating": 2, "comment": "Too vague.", "order_id": order_id},
    )
    assert created.status_code == 201, created.text
    assert client.post(
        "/lawyer/feedback", headers=_auth(lawyer), json={"comment": "x", "order_id": 9999}
    ).status_code in (404, 422)

    listing = client.get("/admin/feedback", headers=_auth(admin)).json()
    assert listing["summary"]["new"] == 1
    assert listing["summary"]["by_category"]["lead_quality"] == {"count": 1, "avg_rating": 2.0}
    item = listing["items"][0]
    assert item["lawyer_name"] == "Dr. Mara Lenz"
    assert item["order_quality_score"] is not None

    updated = client.patch(
        f"/admin/feedback/{item['id']}",
        headers=_auth(admin),
        json={"status": "reviewed", "admin_note": "Tighten intake questions."},
    )
    assert updated.json()["status"] == "reviewed"
    assert client.get(
        "/admin/feedback?status_filter=new", headers=_auth(admin)
    ).json()["items"] == []
    assert client.get("/lawyer/feedback", headers=_auth(lawyer)).json()[0]["status"] == "reviewed"


def test_admin_overview_and_unpublish(client, db_session):
    admin = _admin(client, db_session)
    _lawyer_token, lawyer_id = _approved_lawyer(client, admin)
    _lawyer(client, email="pending@law.de", name="Petra Pending")
    customer = _client(client)
    client.post("/orders", headers=_auth(customer), json={"lawyer_id": lawyer_id, "message": "Hi"})

    data = client.get("/admin/overview", headers=_auth(admin)).json()
    assert data["users"] == {"clients": 1, "lawyers": 2, "admins": 1}
    assert data["lawyers"]["registered"] == 2
    assert data["lawyers"]["live"] == 1
    assert data["lawyers"]["pending_approval"] == 1
    assert data["orders"]["pending"] == 1 and data["orders"]["total"] == 1
    assert data["recent_orders"][0]["lawyer"] == "Dr. Mara Lenz"

    client.patch(
        f"/admin/lawyer-accounts/{lawyer_id}", headers=_auth(admin), json={"is_published": False}
    )
    assert client.post(
        "/orders", headers=_auth(_client(client, "late@example.com")),
        json={"lawyer_id": lawyer_id, "message": "Hi"},
    ).status_code == 404


def test_lead_quality_score():
    assert score_lead({}) == (0, {k: 0 for k in (
        "narrative", "timeline", "documents", "dates", "people", "questions",
        "case_type", "message",
    )})
    full, breakdown = score_lead(SUMMARY, message="x" * 200)
    assert full == 100 and breakdown["narrative"] == 20
    partial, _ = score_lead({"narrative": "short", "case_type": "family"})
    assert 0 < partial < 20
    # Uploaded documents count even if the summary does not list them.
    assert score_lead({}, document_count=3)[1]["documents"] == 20
