import streamlit as st

def main():
    st.title("📊 Analytics")
    st.info("This page is under construction")

if __name__ == "__main__":
    if "user_id" not in st.session_state:
        st.switch_page("🏠_Home.py")
    main()
