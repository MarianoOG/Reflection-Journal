import requests
import streamlit as st

def render_entry():
    pass


def main():
    st.title("✍️ Journal")
    st.write("In here you can write your reflections.")
    

if __name__ == "__main__":
    if "access_token" not in st.session_state:
        st.switch_page("🏠_Home.py")
    main()
