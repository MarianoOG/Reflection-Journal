import requests
import streamlit as st

def analyze_reflection(entry_id: str):
    answer = st.session_state[f"answer_{entry_id}"].strip()
    if not answer:
        return
    
    # Get the reflection
    response = requests.get(f"{st.session_state.backend_url}/reflections/{entry_id}")
    if response.status_code != 200:
        st.error("Failed to get reflection")
        return
    
    # Update the reflection with the answer
    reflection = response.json()
    reflection["answer"] = answer
    response = requests.put(f"{st.session_state.backend_url}/reflections/", json=reflection)
    if response.status_code != 200:
        st.error("Failed to update reflection")
        return
    
    # Analyze the reflection
    response = requests.post(f"{st.session_state.backend_url}/reflections/{entry_id}/analyze")
    if response.status_code != 200:
        st.error("Analysis not generated")
        return
    
    set_current_entry(entry_id)
    return


def delete_entry(entry_id: str):
    response = requests.delete(f"{st.session_state.backend_url}/reflections/{entry_id}")
    if response.status_code != 200:
        st.error("Failed to delete reflection")
    return


def save_for_later(entry_id: str):
    # Get the reflection
    response = requests.get(f"{st.session_state.backend_url}/reflections/{entry_id}")
    if response.status_code != 200:
        st.error("Failed to get reflection")
        return
    
    # Create a new reflection with the same data
    reflection = response.json()
    reflection.pop("id", None)  # Remove ID to create a new one
    response = requests.put(f"{st.session_state.backend_url}/reflections/", json=reflection)
    if response.status_code != 200:
        st.error("Failed to save reflection for later")
        return
    
    # Delete the original reflection
    response = requests.delete(f"{st.session_state.backend_url}/reflections/{entry_id}")
    if response.status_code != 200:
        st.error("Failed to delete original reflection")
    return


def render_entry(entry_id: str, is_child: bool = False):
    # Check if the entry is a child
    if is_child:
        st.divider()

    # Get the entry
    response = requests.get(f"{st.session_state.backend_url}/reflections/{entry_id}")
    if response.status_code != 200:
        st.error("Failed to get reflection")
        return
    entry = response.json()

    # Check if the entry is the current entry and has a parent
    if st.session_state.current_entry_id == entry["id"] and entry["parent_id"]:
        back_col, _ = st.columns([1, 5])
        back_col.button("⬅️ Go back", 
                        key=f"back_{entry['id']}", 
                        on_click=set_current_entry, 
                        args=(entry["parent_id"],))

    # Display the question
    if is_child:
        st.subheader(entry["question"])
    else:
        st.header(entry["question"])

    # Display the context if available
    if entry["context"]:
        st.caption(f"**{entry['type']}**: {entry['context']}")

    # Get themes for the entry
    themes_response = requests.get(f"{st.session_state.backend_url}/reflections/{entry_id}/themes")
    themes = themes_response.json() if themes_response.status_code == 200 else []
    theme_names = [theme["name"] for theme in themes]

    # Display the answer and the sentiment and themes if available
    if theme_names:
        st.write(entry["answer"])
        col1, col2 = st.columns([1, 4])
        col1.pills("Sentiment", [entry["sentiment"]], key=f"sentiment_{entry['id']}", disabled=True)
        col2.pills("Themes", theme_names, key=f"themes_{entry['id']}", disabled=True) 
        
        # Get children
        children_response = requests.get(f"{st.session_state.backend_url}/reflections/{entry_id}/children")
        children = children_response.json() if children_response.status_code == 200 else []
        
        if st.session_state.current_entry_id != entry["id"] and children:
            st.button("Expand", 
                       key=f"expand_{entry['id']}", 
                       on_click=set_current_entry, 
                       args=(entry["id"],),
                       use_container_width=True)
        return
    
    # Display the answer text area
    current_answer = entry["answer"] if entry["answer"] else ""
    current_answer = st.text_area("Reflection", 
                                  value=current_answer, 
                                  key=f"answer_{entry['id']}",
                                  height=250)
    
    # Display the buttons
    col_ignore, _, col_analyze = st.columns([1, 1, 1])
    col_ignore.button("Delete", 
                      key=f"delete_{entry['id']}", 
                      on_click=delete_entry, 
                      args=(entry["id"],),
                      use_container_width=True)
    col_analyze.button("Analyze", 
                        key=f"analyze_{entry['id']}", 
                        on_click=analyze_reflection,
                        args=(entry["id"],),
                        use_container_width=True,
                        type="primary",
                        disabled=not current_answer)


def get_unanswered_reflection_entry():
    response = requests.get(f"{st.session_state.backend_url}/reflections/random/unanswered/{st.session_state.user['id']}")
    if response.status_code == 200:
        entry = response.json()
        set_current_entry(entry["id"])
    else:
        st.info("All entries have been answered")
    return


def set_current_entry(entry_id: str):
    st.session_state.current_entry_id = entry_id


def main():
    # Get user stats
    response = requests.get(f"{st.session_state.backend_url}/users/{st.session_state.user['id']}/stats")
    if response.status_code == 404:
        st.session_state.clear()
        st.switch_page("🏠_Home.py")
    elif response.status_code != 200:
        st.error("Failed to get user stats")
        return
    stats = response.json()
    analyzed_entries = stats["answered_entries"]
    total_entries = stats["total_entries"]

    # Display the sidebar
    st.sidebar.title("Reflection Journal")
    st.sidebar.caption("Analyze and save your reflections")
    metric_col1, metric_col2 = st.sidebar.columns(2)
    metric_col1.metric(label="Entries Analyzed", value=analyzed_entries)
    metric_col2.metric(label="Total Entries", value=total_entries)
    
    # Display the button
    st.sidebar.button("Go to next question", 
                      on_click=get_unanswered_reflection_entry,
                      use_container_width=True,
                      type="primary")

    # Generate insights
    if analyzed_entries == total_entries and analyzed_entries > 0:
        st.info("All entries analyzed.")
        return

    # Get an unanswered reflection
    if "current_entry_id" not in st.session_state:
        get_unanswered_reflection_entry()

    # Get the current entry
    response = requests.get(f"{st.session_state.backend_url}/reflections/{st.session_state.current_entry_id}")
    if response.status_code != 200:
        st.warning("Current entry not found, going back to original entry")
        # Get all reflections and find the first one
        response = requests.get(f"{st.session_state.backend_url}/users/{st.session_state.user['id']}/reflections")
        if response.status_code == 200:
            reflections = response.json()
            if reflections:
                set_current_entry(reflections[0]["id"])
                response = requests.get(f"{st.session_state.backend_url}/reflections/{st.session_state.current_entry_id}")
        if response.status_code != 200:
            st.error("Failed to get reflection")
            st.stop()
    
    current_entry = response.json()
    render_entry(current_entry["id"])
    
    # Get and render children
    children_response = requests.get(f"{st.session_state.backend_url}/reflections/{current_entry['id']}/children")
    if children_response.status_code == 200:
        children = children_response.json()
        for child in children:
            render_entry(child["id"], is_child=True)

if __name__ == "__main__":
    if "user" not in st.session_state:
        st.switch_page("🏠_Home.py")
    main()
