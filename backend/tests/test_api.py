import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_config():
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "provider" in data

def test_analyze():
    response = client.post("/api/v1/analyze", json={"text": "In today's fast-paced world, we must delve into this."})
    assert response.status_code == 200
    data = response.json()
    assert data["robotic_score"] > 0
    assert "in today's fast-paced world" in data["detected_phrases"]
    assert "delve into" in data["detected_phrases"]

def test_humanize():
    payload = {
        "text": "We grew by 50% in Jan 2023.",
        "content_type": "recruiter feedback",
        "tone": "Professional",
        "strength": "medium"
    }
    response = client.post("/api/v1/humanize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "Partial"
    assert "50%" in data["rewritten_text"]

def test_humanize_failure_retry():
    payload = {
        "text": "We grew by 50% FAIL DEMO",
        "content_type": "recruiter feedback",
        "tone": "Professional",
        "strength": "medium"
    }
    response = client.post("/api/v1/humanize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "Failed"
    assert data["rewritten_text"] == payload["text"]
    assert len(data["warnings"]) > 0

def test_validate():
    payload = {
        "original_text": "We have 100 users.",
        "rewritten_text": "We have 100 users total."
    }
    response = client.post("/api/v1/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "Partial"

def test_validate_fail():
    payload = {
        "original_text": "We have 100 users.",
        "rewritten_text": "We have many users."
    }
    response = client.post("/api/v1/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "Failed"

def test_refine():
    payload = {
        "text": "In today's fast-paced world, we scored 85% on 12 March 2026.",
        "options": {
            "writingMode": "Clarity Improvement",
            "context": "General Communication",
            "tone": "Professional",
            "intensity": "Balanced"
        }
    }
    response = client.post("/api/refine", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "timestamp" in data
    assert "revised" in data
    assert "verification" in data
    assert "85%" in data["revised"]
    assert data["verification"]["status"] in ["CONTENT INTEGRITY PASSED", "REVIEW RECOMMENDED", "CONTENT INTEGRITY FAILED"]

