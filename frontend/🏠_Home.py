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

def render_login():
    st.title("Login")
    
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
                    st.switch_page("pages/1_✍️_Journal.py")
    
    with tab2:
        st.write("Create a new account")
        name = st.text_input("Name", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password", 
                                 help="Password must be at least 8 characters long")
        
        if st.button("Register", disabled=not name or not email or not password or len(password) < 8):
            validated_email = check_email(email)
            if validated_email:
                user_response = register_user(name, validated_email, password)
                if user_response:
                    st.success("Account created successfully! Please login with your credentials.")
                    st.rerun()

def main():
    # Title
    st.title("📔 Reflection Journal")
    st.warning("🚧 Under development, your data will be saved to the cloud and used for improving the app.")

    # Login form
    if "access_token" not in st.session_state:
        render_login()
        return
    
    # Welcome message
    st.write("Welcome to your reflection journal. Here you can record your thoughts and reflections.")
    st.info("✨ To start, click on the '✍️ Journal' tab to begin writing! 📝")

if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    st.session_state.backend_url = os.getenv("BACKEND_URL", "http://backend:8080")
    main()
