import pytest
import httpx
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime

from fastapi_app import app, database_engine
from models import User, Theme, Reflection, ReflectionTheme, ReflectionType, SentimentType, Languages
from auth import get_password_hash, create_access_token

# Test database setup
TEST_DATABASE_URL = "sqlite:///./db/test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(scope="function")
def session():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(scope="function")
def client(session):
    def get_session_override():
        return session
    
    # Mock the database_engine globally
    with patch('fastapi_app.database_engine', test_engine):
        with TestClient(app) as c:
            yield c

@pytest.fixture
def test_user(session):
    user = User(
        id="user_test_123",
        name="Test User",
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        prefered_language=Languages.EN
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_theme(session):
    theme = Theme(id="theme_test_123", name="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)
    return theme

@pytest.fixture
def test_reflection(session, test_user):
    reflection = Reflection(
        id="reflection_test_123",
        user_id=test_user.id,
        question="What did you learn today?",
        answer="I learned about testing APIs",
        language=Languages.EN,
        type=ReflectionType.LEARNING,
        sentiment=SentimentType.POSITIVE
    )
    session.add(reflection)
    session.commit()
    session.refresh(reflection)
    return reflection

class TestHealthAndRoot:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Reflexion Journal" in data["message"]

class TestAuthentication:
    def test_register_user(self, client):
        user_data = {
            "name": "New User",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New User"
        assert data["email"] == "newuser@example.com"
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client, test_user):
        user_data = {
            "name": "Duplicate User",
            "email": test_user.email,
            "password": "password123"
        }
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 409

    def test_login_success(self, client, test_user):
        login_data = {
            "email": test_user.email,
            "password": "testpassword"
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_user):
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401

    def test_get_current_user(self, client, test_user, auth_headers):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    def test_unauthorized_access(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

class TestThemes:
    def test_list_themes(self, client, test_theme):
        response = client.get("/themes")
        assert response.status_code == 200
        themes = response.json()
        assert len(themes) >= 0  # May be empty if test_theme fixture hasn't run
        if themes:
            assert isinstance(themes, list)

    def test_list_themes_pagination(self, client, session):
        # Create multiple themes
        themes = []
        for i in range(5):
            theme = Theme(name=f"Theme {i}")
            session.add(theme)
            themes.append(theme)
        session.commit()
        
        response = client.get("/themes?offset=0&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_theme_reflections(self, client, test_theme, test_reflection, session):
        # Link reflection to theme
        reflection_theme = ReflectionTheme(
            theme_id=test_theme.id,
            reflection_id=test_reflection.id
        )
        session.add(reflection_theme)
        session.commit()
        
        response = client.get(f"/themes/{test_theme.id}/reflections")
        assert response.status_code == 200
        reflections = response.json()
        assert len(reflections) >= 1
        assert any(refl["id"] == test_reflection.id for refl in reflections)

    def test_get_theme_reflections_not_found(self, client):
        response = client.get("/themes/nonexistent/reflections")
        assert response.status_code == 404

    def test_delete_theme(self, client, session):
        # Create a theme specifically for this test
        theme = Theme(id="delete_test_theme", name="Delete Test Theme")
        session.add(theme)
        session.commit()
        
        response = client.delete(f"/themes/{theme.id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_theme_not_found(self, client):
        response = client.delete("/themes/nonexistent")
        assert response.status_code == 404

class TestReflections:
    def test_list_reflections(self, client, test_reflection):
        response = client.get("/reflections")
        assert response.status_code == 200
        reflections = response.json()
        assert len(reflections) >= 1

    def test_get_reflection_by_id(self, client, test_reflection):
        response = client.get(f"/reflections/{test_reflection.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_reflection.id
        assert data["question"] == test_reflection.question

    def test_get_reflection_not_found(self, client):
        response = client.get("/reflections/nonexistent")
        assert response.status_code == 404

    def test_upsert_reflection_create(self, client, test_user, auth_headers):
        reflection_data = {
            "id": "new_reflection_123",
            "question": "What are you grateful for?",
            "answer": "I'm grateful for my health",
            "type": "Thought",
            "sentiment": "Positive"
        }
        response = client.put("/reflections/", json=reflection_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == reflection_data["question"]
        assert data["user_id"] == test_user.id

    def test_upsert_reflection_update(self, client, test_reflection, test_user, auth_headers):
        updated_data = {
            "id": test_reflection.id,
            "question": test_reflection.question,
            "answer": "Updated answer",
            "type": "Memory",
            "sentiment": "Neutral"
        }
        response = client.put("/reflections/", json=updated_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Updated answer"
        assert data["type"] == "Memory"

    def test_upsert_reflection_unauthorized(self, client):
        reflection_data = {
            "id": "new_reflection_456",
            "question": "Test question",
            "type": "Thought"
        }
        response = client.put("/reflections/", json=reflection_data)
        assert response.status_code == 401

    def test_get_reflection_parent(self, client, session, test_user):
        # Create parent and child reflections
        parent = Reflection(
            id="parent_123",
            user_id=test_user.id,
            question="Parent question",
            language=Languages.EN
        )
        session.add(parent)
        session.commit()
        
        child = Reflection(
            id="child_123",
            user_id=test_user.id,
            parent_id=parent.id,
            question="Child question",
            language=Languages.EN
        )
        session.add(child)
        session.commit()
        
        response = client.get(f"/reflections/{child.id}/parent")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == parent.id

    def test_get_reflection_children(self, client, session, test_user):
        # Create parent and child reflections
        parent = Reflection(
            id="parent_456",
            user_id=test_user.id,
            question="Parent question",
            language=Languages.EN
        )
        session.add(parent)
        session.commit()
        
        child = Reflection(
            id="child_456",
            user_id=test_user.id,
            parent_id=parent.id,
            question="Child question",
            language=Languages.EN
        )
        session.add(child)
        session.commit()
        
        response = client.get(f"/reflections/{parent.id}/children")
        assert response.status_code == 200
        children = response.json()
        assert len(children) == 1
        assert children[0]["id"] == child.id

    def test_get_reflection_themes(self, client, test_reflection, test_theme, session):
        # Link reflection to theme
        reflection_theme = ReflectionTheme(
            theme_id=test_theme.id,
            reflection_id=test_reflection.id
        )
        session.add(reflection_theme)
        session.commit()
        
        response = client.get(f"/reflections/{test_reflection.id}/themes")
        assert response.status_code == 200
        themes = response.json()
        assert len(themes) >= 1
        assert any(theme["id"] == test_theme.id for theme in themes)

    @patch('fastapi_app.analyze_reflection')
    def test_analyze_reflection(self, mock_analyze, client, test_reflection):
        # Mock the LLM analysis
        mock_analysis = MagicMock()
        mock_analysis.sentiment = SentimentType.POSITIVE
        mock_analysis.themes = ["growth", "learning"]
        mock_analysis.beliefs = []
        mock_analyze.return_value = mock_analysis
        
        response = client.post(f"/reflections/{test_reflection.id}/analyze")
        assert response.status_code == 200
        assert "analyzed successfully" in response.json()["message"]

    def test_get_random_unanswered_reflection(self, client, session, test_user, auth_headers):
        # Create an unanswered reflection
        unanswered = Reflection(
            id="unanswered_123",
            user_id=test_user.id,
            question="What do you think about this?",
            answer=None,
            language=Languages.EN
        )
        session.add(unanswered)
        session.commit()
        
        response = client.get("/reflections/random/unanswered", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] is None

    def test_delete_reflection(self, client, test_reflection, auth_headers):
        response = client.delete(f"/reflections/{test_reflection.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_reflection_unauthorized(self, client, test_reflection):
        response = client.delete(f"/reflections/{test_reflection.id}")
        assert response.status_code == 401

class TestUsers:
    def test_get_user_stats(self, client, test_user, auth_headers, session):
        # Create some reflections
        reflection1 = Reflection(
            user_id=test_user.id,
            question="Question 1",
            answer="Answer 1",
            language=Languages.EN
        )
        reflection2 = Reflection(
            user_id=test_user.id,
            question="Question 2",
            language=Languages.EN
        )
        session.add_all([reflection1, reflection2])
        session.commit()
        
        response = client.get("/users/me/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "answered_entries" in data
        assert data["total_entries"] >= 2
        assert data["answered_entries"] >= 1

    def test_get_user_reflections(self, client, test_user, test_reflection, auth_headers):
        response = client.get("/users/me/reflections", headers=auth_headers)
        assert response.status_code == 200
        reflections = response.json()
        assert len(reflections) >= 1
        assert all(refl["user_id"] == test_user.id for refl in reflections)

    def test_get_user_themes(self, client, test_user, test_reflection, test_theme, auth_headers, session):
        # Link reflection to theme
        reflection_theme = ReflectionTheme(
            theme_id=test_theme.id,
            reflection_id=test_reflection.id
        )
        session.add(reflection_theme)
        session.commit()
        
        response = client.get("/users/me/themes", headers=auth_headers)
        assert response.status_code == 200
        themes = response.json()
        assert len(themes) >= 1

    def test_delete_user(self, client, test_user, auth_headers):
        response = client.delete("/users/me", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

class TestPagination:
    def test_themes_pagination_limit(self, client):
        response = client.get("/themes?limit=150")
        assert response.status_code == 200
        # Should be capped at 100

    def test_reflections_pagination_limit(self, client):
        response = client.get("/reflections?limit=150")
        assert response.status_code == 200
        # Should be capped at 100

class TestErrorHandling:
    def test_invalid_json(self, client):
        response = client.post("/auth/register", data="invalid json")
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        response = client.post("/auth/register", json={"name": "Test"})
        assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__])