import os
import requests
from typing import Optional, Union, List
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

sentiment_emojis = {
    "Positive": "😊",
    "Neutral": "😐",
    "Negative": "😔"
}
    
def login_user(email: str, password: str) -> Optional[dict]:
    """Login user and return token response"""
    with st.spinner("Logging in..."):
        response = requests.post(f"{BACKEND_URL}/auth/login", 
                                json={"email": email, "password": password})
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Incorrect email or password")
        else:
            st.error("Login failed")
        return None

def register_user(name: str, email: str, password: str) -> Optional[dict]:
    """Register new user and return user data"""
    with st.spinner("Creating account..."):
        response = requests.post(f"{BACKEND_URL}/auth/register", 
                                json={"name": name, "email": email, "password": password})
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 409:
            st.error("User with this email already exists")
        else:
            st.error("Registration failed")
        return None

def get_user_info() -> Optional[dict]:
    """Fetch current user information from the backend"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/users/me", 
            headers={"Authorization": f"Bearer {st.session_state.access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to fetch user information")
            return None
    except Exception as e:
        st.error(f"Error fetching user info: {str(e)}")
        return None

def update_user_info(name: str, language: str) -> bool:
    """Update user name and preferred language"""
    try:
        response = requests.put(
            f"{BACKEND_URL}/users/me",
            headers={"Authorization": f"Bearer {st.session_state.access_token}"},
            json={"name": name, "prefered_language": language}
        )
        if response.status_code == 200:
            st.success("Settings updated successfully!")
            return True
        else:
            st.error("Failed to update settings")
            return False
    except Exception as e:
        st.error(f"Error updating settings: {str(e)}")
        return False

def delete_user_account() -> bool:
    """Delete user account"""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/users/me",
            headers={"Authorization": f"Bearer {st.session_state.access_token}"}
        )
        if response.status_code == 200:
            return True
        else:
            st.error("Failed to delete account")
            return False
    except Exception as e:
        st.error(f"Error deleting account: {str(e)}")
        return False

def api_request(method: str, endpoint: str, data: Optional[dict] = None) -> Optional[dict]:
    """Make API request with proper authentication"""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return None
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

def get_reflection(reflection_id: str) -> Optional[dict]:
    """Get a specific reflection by ID"""
    return api_request("GET", f"/reflections/{reflection_id}")

def get_reflections(limit: int = 10, offset: int = 0) -> List[dict]:
    """Get all reflections for the user"""
    # Validate limit and offset
    if limit <= 0:
        limit = 10
    elif limit > 100:
        limit = 100
    if offset < 0:
        offset = 0
    
    result = api_request("GET", "/reflections/", {"limit": limit, "offset": offset})
    return result if result else []

def get_reflection_parent(reflection_id: str) -> Optional[dict]:
    """Get parent reflection"""
    return api_request("GET", f"/reflections/{reflection_id}/parent")

def get_reflection_children(reflection_id: str) -> List[dict]:
    """Get child reflections"""
    result = api_request("GET", f"/reflections/{reflection_id}/children")
    return result if result else []

def save_reflection(reflection_data: dict) -> Optional[dict]:
    """Save (create or update) a reflection"""
    return api_request("PUT", "/reflections/", reflection_data)

def delete_reflection(reflection_id: str) -> bool:
    """Delete a reflection"""
    result = api_request("DELETE", f"/reflections/{reflection_id}")
    return result is not None

def get_reflection_themes(reflection_id: str) -> List[dict]:
    """Get themes associated with a reflection"""
    result = api_request("GET", f"/reflections/{reflection_id}/themes")
    return result if result else []

def analyze_reflection(reflection_id: str) -> Optional[dict]:
    """Analyze a reflection using the AI backend service"""
    return api_request("POST", f"/reflections/{reflection_id}/analyze")

def truncate_text(text: str, n: int):
    truncated_text = text[:n]
    if len(text) > n:
        truncated_text += '...'
    return truncated_text
