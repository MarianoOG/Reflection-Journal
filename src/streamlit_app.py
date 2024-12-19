import streamlit as st
from managers import QuestionManager, ReflectionManager, JournalManager


@st.cache_resource
def get_question_manager() -> QuestionManager:
    return QuestionManager()


@st.cache_resource
def get_reflection_manager() -> ReflectionManager:
    return ReflectionManager()


@st.cache_resource
def get_journal_manager() -> JournalManager:
    reflection_manager = get_reflection_manager()
    return JournalManager(reflection_manager)


def analyze_reflection(entry_id: str):
    answer = st.session_state[f"answer_{entry_id}"].strip()
    if not answer:
        return
    
    reflection_manager = get_reflection_manager()
    entry = reflection_manager.get_reflection_by_id(entry_id)
    if not entry:
        st.error("Entry not found")
        st.stop()
    entry.answer = answer
    reflection_manager.upsert_reflection(entry)
    if not reflection_manager.analyze_reflection_by_id(entry_id):
        st.error("Analysis not generated")
    st.session_state.current_entry_id = entry_id
    return


def ignore_entry(entry_id: str):
    reflection_manager = get_reflection_manager()
    reflection_manager.delete_reflection_by_id(entry_id)
    return


def save_for_later(entry_id: str):
    reflection_manager = get_reflection_manager()
    question_manager = get_question_manager()
    entry = reflection_manager.get_reflection_by_id(entry_id)
    if not entry:
        st.error("Entry not found")
        return
    question_manager.add_question_entry(entry)
    reflection_manager.delete_reflection_by_id(entry_id)
    return


def set_current_entry(entry_id: str):
    st.session_state.current_entry_id = entry_id
    return


def render_entry(entry_id: str, is_child: bool = False):    
    # Get the entry
    reflection_manager = get_reflection_manager()
    entry = reflection_manager.get_reflection_by_id(entry_id)
    if not entry:
        st.error("Entry not found")
        st.stop()

    # Check if the entry is the current entry and has a parent
    if st.session_state.current_entry_id == entry.id and entry.parent_id:
        back_col, _ = st.columns([1, 5])
        back_col.button("⬅️ Go back", 
                        key=f"back_{entry.id}", 
                        on_click=set_current_entry, 
                        args=(entry.parent_id,))

    # Display the question
    st.subheader(entry.question)
    if entry.context:
        st.caption(f"**{entry.context_type}**: {entry.context}")

    # Display the answer and the sentiment and themes if available
    if entry.themes:
        st.write(entry.answer)
        if st.session_state.current_entry_id == entry.id:
            col1, col2 = st.columns([1, 2])
            col1.pills("Sentiment", [entry.sentiment], key=f"sentiment_{entry.id}", disabled=True)
            col2.pills("Themes", entry.themes, key=f"themes_{entry.id}", disabled=True)
        else:
            st.button("Expand", 
                       key=f"expand_{entry.id}", 
                       on_click=set_current_entry, 
                       args=(entry.id,),
                       use_container_width=True)
    else:
        answer = entry.answer if entry.answer else ""
        st.text_area(f"Reflection", 
                        value=answer, 
                        key=f"answer_{entry.id}", 
                        on_change=analyze_reflection,
                        args=(entry.id,),
                        height=150)
        if entry.context_type != "Original":
            col_ignore, col_save_for_later, col_expand, = st.columns([1, 2, 1])
            col_ignore.button("Ignore", 
                                key=f"ignore_{entry.id}", 
                                on_click=ignore_entry, 
                                args=(entry.id,),
                                use_container_width=True)
            col_save_for_later.button("Save for later", 
                                        key=f"save_for_later_{entry.id}", 
                                        on_click=save_for_later,
                                        args=(entry.id,),
                                        use_container_width=True)
            col_expand.button("Expand", 
                                key=f"expand_{entry.id}", 
                                on_click=set_current_entry,
                                args=(entry.id,),
                                use_container_width=True)
    
    # Check if the entry is a child
    st.divider()
    if is_child:
        return
    
    # Render the children entries
    reflection_manager = get_reflection_manager()
    for child in entry.children_ids:
        child_entry = reflection_manager.get_reflection_by_id(child)
        if not child_entry:
            st.error(f"Child entry {child} not found")
            st.stop()
        render_entry(child_entry.id, is_child=True)
    return


def get_unanswered_reflection_entry():
    reflection_manager = get_reflection_manager()
    entry = reflection_manager.get_unanswered_reflection_entry()
    if entry:
        st.session_state.current_entry_id = entry.id
    else:
        st.info("All entries have been answered")
    return


def main():
    # Get the journal manager and stats
    reflection_manager = get_reflection_manager()
    analyzed_entries, total_entries = reflection_manager.get_statistics()

    # Display the sidebar
    st.sidebar.title("Reflection Journal")
    st.sidebar.caption("Analyze and save your reflections")
    metric_col1, metric_col2 = st.sidebar.columns(2)
    metric_col1.metric(label="Entries Analyzed", value=analyzed_entries)
    metric_col2.metric(label="Total Entries", value=total_entries)
    st.sidebar.button("Go to unanswered question", 
                      on_click=get_unanswered_reflection_entry,
                      use_container_width=True)

    # Generate insights
    if analyzed_entries == total_entries and analyzed_entries > 0:
        with st.spinner("All entries analyzed. Generating insights..."):
            journal_manager = get_journal_manager()
            report_analysis = journal_manager.save_journal_entry()
        if report_analysis:
            summary_entry = journal_manager.get_summary_entry()
            if summary_entry:
                st.subheader(summary_entry.question)
                st.write(summary_entry.answer)
            insights = journal_manager.get_insights()
            for insight in insights:
                st.subheader(insight.goal)
                st.write(insight.insight)
                for index, task in enumerate(insight.tasks):
                    st.write(f"{index + 1}. {task}")
            st.sidebar.info(f"{analyzed_entries} entries saved")
            return

    # Initialize the reflection entries
    if total_entries == 0:
        question_manager = get_question_manager()
        question = question_manager.get_random_question_entry()
        original_entry_id = reflection_manager.upsert_reflection(question)
        st.session_state.current_entry_id = original_entry_id

    # Display the current entry
    current_entry = reflection_manager.get_reflection_by_id(st.session_state.current_entry_id)
    if not current_entry:
        st.warning("Current entry not found, going back to original entry")
        if reflection_manager.original_entry_id:
            current_entry = reflection_manager.get_reflection_by_id(reflection_manager.original_entry_id)
        else:
            st.error("Original entry not found")
            st.stop()
    if current_entry:
        render_entry(current_entry.id)


if __name__ == "__main__":
    st.set_page_config(page_icon="📔", page_title="Reflection Journal")
    main()
