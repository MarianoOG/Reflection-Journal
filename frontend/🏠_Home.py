import os
import uuid
import streamlit as st

def render_login():
    st.title("Login")
    st.write("Please enter your name and prefered language to continue")
    user_name = st.text_input("Name")
    user_email = st.text_input("Email")
    user_language = st.selectbox("Language", ["en", "es", "cz"])
    if st.button("Start"):
        st.session_state.user_id = "temp_user_" + str(uuid.uuid4())
        st.session_state.user_name = user_name
        st.session_state.user_email = user_email
        st.session_state.user_language = user_language
        st.rerun()

def main():
    if "user_id" not in st.session_state:
        render_login()
        return
    
    # Title and description
    st.title("📔 Reflection Journal")
    st.write("Welcome to your reflection journal. Here you can record your thoughts and reflections.")
    st.write("To start, click on the 'Journal' tab to begin writing.")

if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    st.session_state.backend_url = os.getenv("BACKEND_URL", "http://backend:8080")
    main()
