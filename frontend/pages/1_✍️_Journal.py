import streamlit as st
from utils import (
    sentiment_emojis,
    get_reflection,
    get_reflections,
    get_reflection_parent,
    get_reflection_children,
    save_reflection,
    delete_reflection
)

def render_edit_mode(reflection: dict = None):
    """Render the edit interface"""
    
    with st.form("reflection_form"):
        if reflection and reflection.get("question"):
            st.write(reflection.get('question'))
            if reflection.get("context"):
                st.caption(f"Context: {reflection.get('context')}")
        else:
            st.write("Write your thoughts...")

        answer = st.text_area(
            "Your Reflection",
            value=reflection.get("answer", "") if reflection else "",
            max_chars=2000,
            height=400,
            help="Your thoughts, insights, or answers"
        )

        _, col1, col2 = st.columns([1, 1, 1])
        
        with col1:
            save_clicked = st.form_submit_button("💾 Save", type="primary", use_container_width=True)
        
        with col2:
            if reflection:
                cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                if cancel_clicked:
                    if reflection:
                        st.session_state.mode = "view"
                        st.rerun()
                    else:
                        st.switch_page("🏠_Home.py")
        
        if save_clicked:
            if not answer.strip():
                st.error("Answer is required!")
                return
            
            reflection_data = {
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
            

def render_view_mode(reflection: dict):
    """Render the view interface"""
    # Subtitle
    st.subheader(f"{reflection['question']}")
    if reflection.get("context"):
        st.caption(f"Context: {reflection['context']}")
    
    # Answer
    if reflection.get("answer"):
        st.markdown(reflection["answer"])
    else:
        st.warning("No reflection content yet. Click Edit to add your thoughts.")

    # Render sentiment
    sentiment_emoji = sentiment_emojis.get(reflection["sentiment"], "😐")
    st.metric("Sentiment", f"{sentiment_emoji} {reflection['sentiment']}")

    render_actions(reflection)
    
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
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✏️ Edit", type="primary", use_container_width=True):
            st.session_state.mode = "edit"
            st.rerun()

    with col2:
        if st.button("👶 Add Child", disabled=True, use_container_width=True):
            st.session_state.current_reflection_id = None
            st.session_state.parent_id = reflection["id"]
            st.session_state.mode = "edit"
            st.rerun()

    with col3:
        if st.button("🗑️ Delete", type="secondary", use_container_width=True):
            if delete_reflection(reflection["id"]):
                st.success("Reflection deleted!")
                st.session_state.current_reflection_id = None
                st.rerun()
            else:
                st.error("Failed to delete reflection")

def render_reflection_list():
    """Render a sidebar with all reflections for navigation"""
    with st.sidebar:
        if st.button("➕ New Entry", type="primary", use_container_width=True):
            st.session_state.current_reflection_id = None
            st.session_state.mode = "edit"
            st.rerun()

        st.header("📚 Recent Reflections")
        
        reflections = get_reflections(10)
        if reflections:
            for reflection in reflections:
                # Show emoji based on whether it's a parent (user entry) or child (AI question)
                emoji = "🤔" if reflection.get("parent_id") else "💭"
                if st.button(f"{emoji} {reflection['question'][:25]}...",
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
