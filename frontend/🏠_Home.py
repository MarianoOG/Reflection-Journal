import os
import uuid
import requests
from typing import Optional
from email_validator import validate_email, EmailNotValidError
import streamlit as st

@st.cache_data(ttl=60)
def get_user_by_email(user_email: str) -> Optional[dict]:
    response = requests.get(f"{st.session_state.backend_url}/users/{user_email}")
    if response.status_code == 200:
        return response.json()
    return None

def create_user(user_name: str, user_email: str, user_language: str) -> Optional[str]:
    # Get user stats
    with st.spinner("Creating user..."):
        response = requests.post(f"{st.session_state.backend_url}/users/", 
                                    json={"name": user_name, 
                                          "email": user_email,
                                          "prefered_language": user_language})
        if response.status_code != 200:
            st.error("Failed to create user")
            return None
        return response.json()

def check_email(user_email: str, check_deliverability: bool = False) -> Optional[str]:
    try:
        email_info = validate_email(user_email, check_deliverability=check_deliverability)
        return email_info.normalized
    except EmailNotValidError:
        st.error("Email is not valid")
        return None

def render_login():
    st.title("Login")
    st.write("Please enter your name, email and prefered language to continue")
    user_email = st.text_input("Email")
    if user_email == "":
        return
    user_email = check_email(user_email)
    if user_email is not None:
        user = get_user_by_email(user_email)
        if user is None:
            user_name = st.text_input("Name")
            language_options = {
                "en": "🇬🇧 English",
                "es": "🇲🇽 Español",
                "cz": "🇨🇿 Čeština"
            }
            user_language = st.selectbox(
                "Prefered language",
                options=list(language_options.keys()),
                format_func=lambda x: language_options[x]
            )
            if st.button("Start", disabled=user_name == ""):
                st.session_state.user = create_user(user_name, user_email, user_language)
                st.switch_page("pages/1_✍️_Journal.py")
        else:
            st.session_state.user = user
            st.switch_page("pages/1_✍️_Journal.py")

def main():
    # Title
    st.title("📔 Reflection Journal")
    st.warning("🚧 Under development, your data will be saved to the cloud and used for improving the app.")

    # Login form
    if "user" not in st.session_state:
        render_login()
        return
    
    # Welcome message
    st.write("Welcome to your reflection journal. Here you can record your thoughts and reflections.")
    st.info("✨ To start, click on the '✍️ Journal' tab to begin writing! 📝")

if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    st.session_state.backend_url = os.getenv("BACKEND_URL", "http://backend:8080")
    main()
