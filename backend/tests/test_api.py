from datetime import datetime, timedelta, timezone


def _seed_one_instance(client):
    from app import models
    from app.db import get_db

    db = next(client.app.dependency_overrides[get_db]())

    inst = models.Instance(
        cloud_instance_id="i-test-001",
        cloud_provider="aws",
        region="us-east-2",
        environment="prod",
        instance_type="t3.micro",
        hourly_cost=0.0104,
        tags={"test": True},
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    now = datetime.now(timezone.utc)
    for i in range(48):
        ts = now - timedelta(hours=i)
        db.add(
            models.Metric(
                instance_id=inst.id,
                timestamp=ts,
                cpu_utilization=10.0,
                mem_utilization=10.0,
                network_in_bytes=1000,
                network_out_bytes=2000,
            )
        )
    db.commit()
    return inst.id


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_instances_list(client):
    _seed_one_instance(client)
    r = client.get("/instances")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["cloud_instance_id"] == "i-test-001"


def test_actions_create_and_verify_with_stubbed_aws(client, monkeypatch):
    inst_id = _seed_one_instance(client)

    r = client.post("/actions", json={"instance_id": inst_id, "new_instance_type": "t3.small"})
    assert r.status_code == 200
    action = r.json()
    assert action["status"] in ("pending", "verified")
    action_id = action["id"]

    import app.routers.actions as actions_router

    monkeypatch.setattr(actions_router, "_get_ec2_instance_type", lambda *_args, **_kwargs: "t3.small")

    r2 = client.post(f"/actions/{action_id}/verify")
    assert r2.status_code == 200
    verified = r2.json()
    assert verified["status"] == "verified"
    assert verified["verified_at"] is not None


def test_metrics_endpoint(client):
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "ccopt_http_requests_total" in text
    assert "ccopt_http_request_duration_ms" in text
    assert "ccopt_verify_actions_total" in text


