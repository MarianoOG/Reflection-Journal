import streamlit as st
import requests
import os
from typing import Optional

def get_user_info() -> Optional[dict]:
    """Fetch current user information from the backend"""
    try:
        response = requests.get(
            f"{st.session_state.backend_url}/users/me", 
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
            f"{st.session_state.backend_url}/users/me",
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
            f"{st.session_state.backend_url}/users/me",
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

def main():
    st.title("⚙️ Settings")
    
    # Get current user info
    user_info = get_user_info()
    if not user_info:
        st.error("Unable to load user settings")
        return
    
    # User Information Section
    st.divider()
    st.header("👤 User Information")
    
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
        if update_user_info(name, selected_language):
            st.rerun()
    
    st.divider()
    
    # Account Information (read-only)
    st.header("📋 Account Information")
    st.text_input("Email", value=user_info.get("email", ""), disabled=True)
    st.text_input("Created", value=user_info.get("created_at", "")[:10], disabled=True)
    st.text_input("Last Login", value=user_info.get("last_login", "")[:10], disabled=True)
    st.divider()
    
    # Danger Zone
    st.header("⚠️ Danger Zone")
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

if __name__ == "__main__":    
    if "access_token" not in st.session_state:
        st.switch_page("🏠_Home.py")
    main()
