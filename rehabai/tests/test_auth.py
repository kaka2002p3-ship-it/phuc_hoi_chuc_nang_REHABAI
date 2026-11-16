import uuid
from fastapi.testclient import TestClient
from backend.main import app


def test_register_login_and_me():
    client=TestClient(app); email=f"user-{uuid.uuid4()}@example.com"; password="safe-password-123"
    registered=client.post("/api/auth/register",json={"email":email,"full_name":"Người kiểm thử","password":password})
    assert registered.status_code==201
    logged=client.post("/api/auth/login",json={"email":email,"password":password})
    assert logged.status_code==200
    token=logged.json()["access_token"]
    assert client.get("/api/users/me",headers={"Authorization":f"Bearer {token}"}).status_code==200


def test_profile_can_be_updated_without_changing_login():
    client=TestClient(app); email=f"profile-{uuid.uuid4()}@example.com"; password="safe-password-123"
    registered=client.post("/api/auth/register",json={"email":email,"full_name":"Hồ sơ thử","password":password}).json()
    headers={"Authorization":f"Bearer {registered['access_token']}"}
    payload={"full_name":"Tên đã sửa","phone":"0900000000","bio":"Đang luyện tập mỗi ngày.","avatar_data_url":None,"weekly_goal":4,"height_cm":165.5,"weight_kg":58.2}
    updated=client.put("/api/users/me",headers=headers,json=payload)
    assert updated.status_code==200
    body=updated.json()
    assert body["email"]==email and body["full_name"]=="Tên đã sửa"
    assert body["weekly_goal"]==4 and body["height_cm"]==165.5
    assert client.post("/api/auth/login",json={"email":email,"password":password}).status_code==200


def test_profile_rejects_non_image_avatar():
    client=TestClient(app); email=f"avatar-{uuid.uuid4()}@example.com"
    registered=client.post("/api/auth/register",json={"email":email,"full_name":"Avatar thử","password":"safe-password-123"}).json()
    response=client.put("/api/users/me",headers={"Authorization":f"Bearer {registered['access_token']}"},json={"full_name":"Avatar thử","avatar_data_url":"data:text/html;base64,SGVsbG8=","weekly_goal":3})
    assert response.status_code==422
