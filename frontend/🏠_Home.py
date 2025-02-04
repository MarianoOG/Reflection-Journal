import os
import uuid
import streamlit as st

def render_card(emoji: str, title: str, description: str):
    st.markdown(f"""
        <div style="margin: 1rem; padding: 1rem; border-radius: 10px; background: linear-gradient(to right, #4880EC, #019CAD); text-align: center;">
            <h3 style="color: white;">{emoji} {title}</h3>
            <p style="color: white;">{description}</p>
            <a href="/{title}" style="color: white; text-decoration: none;">
                <button style="background-color: white; color: '#4880EC'; text-color: #ffffff; border: none; padding: 0.5rem 1rem; border-radius: 5px; cursor: pointer;">
                    Go to {title}
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)


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

    # Hero banners for navigation
    col1, col2, col3 = st.columns(3)

    with col1:
        render_card('✍️', 'Journal', 'Record your thoughts and reflections')

    with col2:
        render_card('📊', 'Analytics', 'View insights from your journal entries')

    with col3:
        render_card('⚙️', 'Settings', 'Customize your journal experience')


if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    st.session_state.backend_url = os.getenv("BACKEND_URL", "http://backend:8080")
    main()
