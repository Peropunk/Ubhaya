"""P1.1 scaffold and P1.2 intake through the HTTP API."""
import hashlib


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_list_case(client):
    r = client.post("/cases", json={"title": "Test case", "synthetic": True})
    assert r.status_code == 201
    case = r.json()
    assert case["id"] == "C001" and case["timezone"] == "Asia/Kolkata" and case["synthetic"] is True
    assert [c["id"] for c in client.get("/cases").json()] == ["C001"]


def test_upload_hash_and_verify(client):
    cid = client.post("/cases", json={"title": "Upload"}).json()["id"]
    body = b"time,badge_id,holder,door,direction\n2025-12-03 21:52:07,E-1,A,MAIN,OUT\n"
    r = client.post(f"/cases/{cid}/artifacts", files={"file": ("door.csv", body, "text/csv")},
                    data={"type": "door_log", "source": "test", "meta": '{"timezone": "Asia/Kolkata"}'})
    assert r.status_code == 201, r.text
    art = r.json()
    assert art["sha256"] == hashlib.sha256(body).hexdigest()
    assert art["size"] == len(body) and art["meta"] == {"timezone": "Asia/Kolkata"}
    v = client.get(f"/artifacts/{art['id']}/verify").json()
    assert v["ok"] is True and v["actual"] == art["sha256"]
    assert client.get(f"/artifacts/{art['id']}/content").content == body
    chain = client.get(f"/cases/{cid}/audit/verify").json()
    assert chain == {"ok": True, "entries": 3, "broken_at": None, "reason": None}  # created, registered, verified
    actions = [e["action"] for e in client.get(f"/cases/{cid}/audit").json()]
    assert actions == ["case_created", "artifact_registered", "artifact_verified"]


def test_unknown_ids_404(client):
    assert client.get("/cases/C999").status_code == 404
    assert client.get("/artifacts/A999/verify").status_code == 404


def test_bad_artifact_type_rejected(client):
    cid = client.post("/cases", json={"title": "x"}).json()["id"]
    r = client.post(f"/cases/{cid}/artifacts", files={"file": ("a.bin", b"x")}, data={"type": "mystery", "source": "t"})
    assert r.status_code == 422


def test_ui_served(client):
    r = client.get("/ui/")
    assert r.status_code == 200 and "UBHAYA" in r.text
