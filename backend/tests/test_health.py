def test_health_reports_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_runs_against_temporary_sqlite_file(client, settings):
    client.get("/api/health")

    assert settings.database_path.exists()
