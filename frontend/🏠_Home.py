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


def main():
    # Title and description
    st.title("📔 Reflection Journal")

    # Hero banners for navigation
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        render_card('✍️', 'Journal', 'Record your thoughts and reflections')

    with col2:
        render_card('📊', 'Analytics', 'View insights from your journal entries')

    with col3:
        render_card('🎯', 'Goals', 'Set and track your personal goals')

    with col4:
        render_card('⚙️', 'Settings', 'Customize your journal experience')


if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    main()
