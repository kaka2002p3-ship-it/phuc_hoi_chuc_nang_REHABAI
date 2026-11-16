import uuid


def auth(client):
    email = f"user-{uuid.uuid4()}@example.com"
    data = client.post("/api/auth/register", json={
        "email": email, "full_name": "Người kiểm thử", "password": "safe-password-123",
    }).json()
    return {"Authorization": f"Bearer {data['access_token']}"}
