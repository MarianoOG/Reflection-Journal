import streamlit as st
from utils import get_user_info, update_user_info, delete_user_account
from footer import render_sidebar_footer

def main():
    st.title("⚙️ Settings")

    # Get current user info
    user_info = get_user_info()
    if not user_info:
        st.error("Unable to load user settings")
        return
    
    # User Information Section
    st.divider()
    st.subheader("👤 User Information")
    
    # Name input
    name = st.text_input(
        "Name", 
        value=user_info.get("name", ""),
        help="Your display name"
    )
    
    language_options = {
        "en": "🇺🇸 English",
        "es": "🇪🇸 Español", 
        "cz": "🇨🇿 Čeština"
    }
    
    current_language = user_info.get("prefered_language", "en")
    selected_language = st.selectbox(
        "Preferred Language",
        options=list(language_options.keys()),
        format_func=lambda x: language_options[x],
        index=list(language_options.keys()).index(current_language)
    )
    
    # Update button
    if st.button("💾 Save Changes", type="primary"):
        if name and update_user_info(name, selected_language):
            st.rerun()
    
    st.divider()
    
    # Account Information (read-only)
    st.subheader("📋 Account Information")
    st.text_input("Email", value=user_info.get("email", ""), disabled=True)
    st.text_input("Created", value=user_info.get("created_at", "")[:10], disabled=True)
    st.text_input("Last Login", value=user_info.get("last_login", "")[:10], disabled=True)
    st.divider()
    
    # Danger Zone
    st.subheader("⚠️ Danger Zone")
    st.warning("The following actions cannot be undone!")
    
    with st.expander("🗑️ Delete Account", expanded=False):
        st.write("This will permanently delete your account and all associated data.")
        confirm_deletion = st.checkbox(
            "I understand that this action cannot be undone",
            key="delete_account_checkbox"
        )
        
        if st.button(
            "🗑️ Delete Account", 
            type="secondary",
            disabled=not confirm_deletion,
            key="delete_account_button"
        ):
            if delete_user_account():
                st.success("Account deleted successfully. You will be logged out.")
                # Clear session state and redirect to home
                for key in ['access_token', 'token_type', 'user_email']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.switch_page("🏠_Home.py")

    # Render footer with logout and feedback
    render_sidebar_footer()

if __name__ == "__main__":
    st.set_page_config(layout="centered", page_icon="⚙️", page_title="Settings")
    if "access_token" not in st.session_state:
        st.switch_page("🏠_Home.py")
    st.session_state["Page"] = "Settings"
    main()
