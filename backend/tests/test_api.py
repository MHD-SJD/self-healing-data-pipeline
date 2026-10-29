def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["database"] == "HEALTHY"


def test_list_pipelines(client):
    response = client.get("/api/v1/pipelines")
    assert response.status_code == 200
    pipelines = response.json()
    assert len(pipelines) >= 3
    ids = [p["pipeline_id"] for p in pipelines]
    assert "e_commerce_orders_pipeline" in ids
    assert "customers_pipeline" in ids
    assert "inventory_pipeline" in ids


def test_list_runs(client):
    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)


def test_quality_score(client):
    response = client.get("/api/v1/quality/score")
    assert response.status_code == 200
    score_data = response.json()
    assert "overall_score" in score_data
    assert score_data["overall_score"] >= 0.0


def test_metrics_scrape(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "python_gc_objects_collected_total" in response.text or "process_cpu_seconds_total" in response.text or "pipeline" in response.text

