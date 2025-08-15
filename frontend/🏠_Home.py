import os
import requests
from typing import Optional
from email_validator import validate_email, EmailNotValidError
import streamlit as st

def login_user(email: str, password: str) -> Optional[dict]:
    """Login user and return token response"""
    with st.spinner("Logging in..."):
        response = requests.post(f"{st.session_state.backend_url}/auth/login", 
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
        response = requests.post(f"{st.session_state.backend_url}/auth/register", 
                                json={"name": name, "email": email, "password": password})
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 409:
            st.error("User with this email already exists")
        else:
            st.error("Registration failed")
        return None

def check_email(user_email: str, check_deliverability: bool = False) -> Optional[str]:
    try:
        email_info = validate_email(user_email, check_deliverability=check_deliverability)
        return email_info.normalized
    except EmailNotValidError:
        st.error("Email is not valid")
        return None


def get_reflections(limit: Optional[int] = None):
    url = f"{st.session_state.backend_url}/reflections"
    if limit:
        url += f"?limit={limit}"
    response = requests.get(url, headers={"Authorization": f"Bearer {st.session_state.access_token}"})
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to get reflections")
        return None
    

def render_login():
    st.title("📔 Reflection Journal - Login")
    
    # Toggle between login and register
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.write("Please enter your email and password")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", disabled=not email or not password):
            validated_email = check_email(email)
            if validated_email:
                token_response = login_user(validated_email, password)
                if token_response:
                    st.session_state.access_token = token_response["access_token"]
                    st.session_state.token_type = token_response["token_type"]
                    st.session_state.user_email = validated_email
                    st.success("Login successful!")
                    st.rerun()
    
    with tab2:
        st.write("Create a new account")
        name = st.text_input("Name", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password", 
                                 help="Password must be at least 8 characters long")
        confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")
        
        # Check if passwords match
        passwords_match = password == confirm_password if password and confirm_password else True
        if not passwords_match and confirm_password:
            st.error("Passwords do not match")
        
        register_disabled = (not name or not email or not password or not confirm_password or 
                           len(password) < 8 or not passwords_match)
        
        if st.button("Register", disabled=register_disabled):
            validated_email = check_email(email)
            if validated_email:
                user_response = register_user(name, validated_email, password)
                if user_response:
                    st.success("Account created successfully! Logging you in...")
                    # Auto-login after successful registration
                    token_response = login_user(validated_email, password)
                    if token_response:
                        st.session_state.access_token = token_response["access_token"]
                        st.session_state.token_type = token_response["token_type"]
                        st.session_state.user_email = validated_email
                        st.rerun()
            else:
                st.error("Email verification failed")


def render_reflections():    
    # Create columns for layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Recent entries")
    
    with col2:
        if st.button("New entry", key="create_new_entry", type="primary", use_container_width=True):
            st.switch_page("pages/1_✍️_Journal.py")

    reflections = get_reflections(limit=10)
    if reflections:
        for reflection in reflections:
            render_entry(reflection)
    else:
        st.info("No reflections found, create a new entry to get started.")
        

def render_entry(reflection: dict):
    st.write("- " + reflection["question"])


def main():
    # Warning
    st.sidebar.warning("🚧 Under development, your data will be saved to the cloud and used for improving the app.")

    # Login form
    if "access_token" not in st.session_state:
        render_login()
        return
    
    # Title
    st.title("📔 Reflection Journal")
    
    # Render reflections
    render_reflections()

    # Logout button in sidebar
    with st.sidebar:
        st.write(f"Logged in as: {st.session_state.get('user_email', 'Unknown')}")
        if st.button("Logout"):
            # Clear session state
            for key in ['access_token', 'token_type', 'user_email']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    st.session_state.backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
    main()
