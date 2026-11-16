from fastapi.testclient import TestClient
from backend.main import app
from test_helpers import auth

def test_report_endpoints():
    client=TestClient(app); headers=auth(client)
    summary=client.get("/api/reports/summary",headers=headers); progress=client.get("/api/reports/progress?days=30",headers=headers)
    assert summary.status_code==200 and "completion_rate" in summary.json()
    assert progress.status_code==200 and isinstance(progress.json(),list)
