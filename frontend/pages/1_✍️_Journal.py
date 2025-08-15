import requests
import streamlit as st
import uuid
from typing import Optional, List

sentiment_emojis = {
    "Positive": "😊",
    "Neutral": "😐", 
    "Negative": "😔"
}

type_emojis = {
    "Thought": "💭",
    "Memory": "🧠",
    "Learning": "📚",
    "Summary": "📝",
    "Assumption": "🤔",
    "Blind Spot": "👁️",
    "Contradiction": "⚖️"
}

def api_request(method: str, endpoint: str, data: dict = None) -> Optional[dict]:
    """Make API request with proper authentication"""
    url = f"{st.session_state.backend_url}{endpoint}"
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

def get_reflection(reflection_id: str) -> Optional[dict]:
    """Get a specific reflection by ID"""
    return api_request("GET", f"/reflections/{reflection_id}")

def get_reflections() -> List[dict]:
    """Get all reflections for the user"""
    result = api_request("GET", "/reflections/")
    return result if result else []

def get_reflection_parent(reflection_id: str) -> Optional[dict]:
    """Get parent reflection"""
    return api_request("GET", f"/reflections/{reflection_id}/parent")

def get_reflection_children(reflection_id: str) -> List[dict]:
    """Get child reflections"""
    result = api_request("GET", f"/reflections/{reflection_id}/children")
    return result if result else []

def save_reflection(reflection_data: dict) -> Optional[dict]:
    """Save (create or update) a reflection"""
    return api_request("PUT", "/reflections/", reflection_data)

def delete_reflection(reflection_id: str) -> bool:
    """Delete a reflection"""
    result = api_request("DELETE", f"/reflections/{reflection_id}")
    return result is not None

def render_edit_mode(reflection: dict = None):
    """Render the edit interface"""
       
    answer = st.text_area(
        "Your Reflection",
        value=reflection.get("answer", "") if reflection else "",
        max_chars=2000,
        height=400,
        help="Your thoughts, insights, or answers"
    )

    col1, col2 = st.columns([1, 1])
    
    with col1:
        save_clicked = st.form_submit_button("💾 Save", 
                                                type="primary")
    
    with col2:
        if reflection:
            cancel_clicked = st.form_submit_button("❌ Cancel")
        else:
            cancel_clicked = False
    
    if save_clicked:
        if not answer.strip():
            st.error("Answer is required!")
            return
        
        reflection_data = {
            "type": reflection.get("type", "") if reflection else "Thought",
            "language": reflection.get("language", "") if reflection else "en",
            "sentiment": reflection.get("sentiment", "") if reflection else "Neutral",
            "parent_id": reflection.get("parent_id", "") if reflection else None,
            "context": reflection.get("context", "") if reflection else None,
            "question": reflection.get("question", "") if reflection else "",
            "answer": answer if answer.strip() else None
        }

        if reflection:
            reflection_data["id"] = reflection["id"]
        
        result = save_reflection(reflection_data)
        if result:
            st.success("Reflection saved successfully! 🎉")
            st.session_state.current_reflection_id = result["id"]
            st.session_state.mode = "view"
            st.rerun()
        else:
            st.error("Failed to save reflection")
    
        if cancel_clicked:
            if reflection:
                st.session_state.mode = "view"
                st.rerun()
            else:
                st.switch_page("🏠_Home.py")

def render_view_mode(reflection: dict):
    """Render the view interface"""
    col1, col2 = st.columns([4, 1])
    
    with col1:
        type_emoji = type_emojis.get(reflection["type"], "💭")
        sentiment_emoji = sentiment_emojis.get(reflection["sentiment"], "😐")
        st.subheader(f"{type_emoji} {reflection['question']}")
    
    with col2:
        if st.button("✏️ Edit", type="primary"):
            st.session_state.mode = "edit"
            st.rerun()

    render_actions(reflection)
    
    with st.container():
        st.markdown("### Details")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Type", f"{type_emoji} {reflection['type']}")
        with col2:
            st.metric("Sentiment", f"{sentiment_emoji}")
        
        if reflection.get("context"):
            st.caption(f"Context: {reflection['context']}")
        
        if reflection.get("answer"):
            st.markdown("**Your Reflection:**")
            st.markdown(reflection["answer"])
        else:
            st.warning("No reflection content yet. Click Edit to add your thoughts.")
    
    render_relationships(reflection)

def render_relationships(reflection: dict):
    """Render parent and children relationships"""
    st.markdown("### 🔗 Relationships")
    
    with st.expander("⬆️ Parent"):
        parent = get_reflection_parent(reflection["id"])
        if parent:
            if st.button(f"{parent['question'][:50]}...", key="parent_btn"):
                st.session_state.current_reflection_id = parent["id"]
                st.rerun()
        else:
            st.info("This entry has no parent")

    with st.expander("⬇️ Children"):
        children = get_reflection_children(reflection["id"])
        if children:
            for i, child in enumerate(children):
                if st.button(f"{child['question'][:50]}...", key=f"child_{i}"):
                    st.session_state.current_reflection_id = child["id"]
                    st.rerun()
        else:
            st.info("This entry has no children")

def render_actions(reflection: dict):
    """Render action buttons"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ New Reflection"):
            st.session_state.current_reflection_id = None
            st.session_state.mode = "edit"
            st.rerun()
    
    with col2:
        if st.button("👶 Add Child"):
            st.session_state.current_reflection_id = None
            st.session_state.parent_id = reflection["id"]
            st.session_state.mode = "edit"
            st.rerun()
    
    with col3:
        if st.button("🏠 Home"):
            st.switch_page("🏠_Home.py")
    
    with col4:
        if st.button("🗑️ Delete", type="secondary"):
            if delete_reflection(reflection["id"]):
                st.success("Reflection deleted!")
                st.session_state.current_reflection_id = None
                st.rerun()
            else:
                st.error("Failed to delete reflection")

def render_reflection_list():
    """Render a sidebar with all reflections for navigation"""
    with st.sidebar:
        st.header("📚 All Reflections")
        
        reflections = get_reflections()
        if reflections:
            for reflection in reflections[:10]:  # Show recent 10
                type_emoji = type_emojis.get(reflection["type"], "💭")
                if st.button(f"{type_emoji} {reflection['question'][:30]}...", 
                           key=f"nav_{reflection['id']}", 
                           use_container_width=True):
                    st.session_state.current_reflection_id = reflection["id"]
                    st.session_state.mode = "view"
                    st.rerun()
        else:
            st.info("No reflections yet")

def main():    
    # Initialize session state
    if "mode" not in st.session_state:
        st.session_state.mode = "edit"  # Start in edit mode for new entries
    
    if "current_reflection_id" not in st.session_state:
        st.session_state.current_reflection_id = None
    
    if "parent_id" not in st.session_state:
        st.session_state.parent_id = None
    
    # Render navigation sidebar
    render_reflection_list()
    
    # Handle URL parameters or session state
    current_id = st.session_state.current_reflection_id
    mode = st.session_state.mode
    
    if current_id and mode == "view":
        # View existing reflection
        st.title("✍️ Journal")
        reflection = get_reflection(current_id)
        if reflection:
            render_view_mode(reflection)
        else:
            st.error("Reflection not found")
            st.session_state.current_reflection_id = None
            st.rerun()
    
    elif current_id and mode == "edit":
        # Edit existing reflection
        st.title("✍️ Journal - Edit")
        reflection = get_reflection(current_id)
        if reflection:
            render_edit_mode(reflection)
        else:
            st.error("Reflection not found")
            st.session_state.current_reflection_id = None
            st.rerun()
            
    else:
        # Create new reflection
        st.title("✍️ Journal - New")
        base_reflection = {}
        if st.session_state.parent_id:
            base_reflection["parent_id"] = st.session_state.parent_id
            st.session_state.parent_id = None  # Clear after use
        
        render_edit_mode(base_reflection if base_reflection else None)

if __name__ == "__main__":
    if "access_token" not in st.session_state:
        st.switch_page("🏠_Home.py")
    main()
