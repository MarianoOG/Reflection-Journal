import streamlit as st
from managers import QuestionManager, ReflectionManager, JournalManager


@st.cache_resource
def get_question_manager() -> QuestionManager:
    file_path = "data/questions.jsonl"
    return QuestionManager(file_path)


@st.cache_resource
def get_reflection_manager(user_id: str) -> ReflectionManager:
    return ReflectionManager(user_id)


@st.cache_resource
def get_journal_manager(user_id: str) -> JournalManager:
    reflection_manager = get_reflection_manager(user_id)
    return JournalManager(reflection_manager)


def set_current_entry(entry_id: str):
    st.session_state.current_entry_id = entry_id
    return


def analyze_reflection(entry_id: str):
    answer = st.session_state[f"answer_{entry_id}"].strip()
    if not answer:
        return
    
    reflection_manager = get_reflection_manager(st.session_state.user_id)
    entry = reflection_manager.get_reflection_by_id(entry_id)
    if not entry:
        st.error(f"Entry {entry_id} not found")
        return
    
    entry.answer = answer
    reflection_manager.upsert_reflection(entry)
    if not reflection_manager.analyze_reflection_by_id(entry_id):
        st.error(f"Analysis not generated for entry {entry_id}")
    set_current_entry(entry_id)
    return


def ignore_entry(entry_id: str):
    reflection_manager = get_reflection_manager(st.session_state.user_id)
    reflection_manager.delete_reflection_by_id(entry_id)
    return


def save_for_later(entry_id: str):
    reflection_manager = get_reflection_manager(st.session_state.user_id)
    question_manager = get_question_manager()
    entry = reflection_manager.get_reflection_by_id(entry_id)
    if not entry:
        st.error("Entry not found")
        return
    question_manager.add_question_entry(entry)
    reflection_manager.delete_reflection_by_id(entry_id)
    return


def render_entry(entry_id: str, is_child: bool = False):
    # Check if the entry is a child
    if is_child:
        st.divider()

    # Get the entry
    reflection_manager = get_reflection_manager(st.session_state.user_id)
    entry = reflection_manager.get_reflection_by_id(entry_id)
    if not entry:
        st.error(f"Entry {entry_id} not found")
        return

    # Check if the entry is the current entry and has a parent
    if st.session_state.current_entry_id == entry.id and entry.parent_id:
        back_col, _ = st.columns([1, 5])
        back_col.button("⬅️ Go back", 
                        key=f"back_{entry.id}", 
                        on_click=set_current_entry, 
                        args=(entry.parent_id,))

    # Display the question
    if is_child:
        st.subheader(entry.question)
    else:
        st.header(entry.question)

    # Display the context if available
    if entry.context:
        st.caption(f"**{entry.context_type}**: {entry.context}")

    # Display the answer and the sentiment and themes if available
    if entry.themes:
        st.write(entry.answer)
        col1, col2 = st.columns([1, 4])
        col1.pills("Sentiment", [entry.sentiment], key=f"sentiment_{entry.id}", disabled=True)
        col2.pills("Themes", entry.themes, key=f"themes_{entry.id}", disabled=True) 
        if st.session_state.current_entry_id != entry.id and entry.children_ids:
            st.button("Expand", 
                       key=f"expand_{entry.id}", 
                       on_click=set_current_entry, 
                       args=(entry.id,),
                       use_container_width=True)
        return
    
    # Display the answer text area
    current_answer = entry.answer if entry.answer else ""
    current_answer = st.text_area("Reflection", 
                                  value=current_answer, 
                                  key=f"answer_{entry.id}",
                                  height=250)
    
    # Display the buttons
    col_ignore, col_save_for_later, col_analyze = st.columns([1, 1, 1])
    col_ignore.button("Ignore", 
                      key=f"ignore_{entry.id}", 
                      on_click=ignore_entry, 
                      args=(entry.id,),
                      use_container_width=True,
                      disabled= entry.context_type == "Original")
    col_save_for_later.button("Save for later", 
                              key=f"save_for_later_{entry.id}", 
                              on_click=save_for_later,
                              args=(entry.id,),
                              use_container_width=True)
    col_analyze.button("Analyze", 
                        key=f"analyze_{entry.id}", 
                        on_click=analyze_reflection,
                        args=(entry.id,),
                        use_container_width=True,
                        type="primary",
                        disabled=not current_answer)


def get_unanswered_reflection_entry():
    reflection_manager = get_reflection_manager(st.session_state.user_id)
    entry = reflection_manager.get_unanswered_reflection_entry()
    if entry:
        set_current_entry(entry.id)
    else:
        st.info("All entries have been answered")
        get_final_analysis()
    return


def get_final_analysis():
    with st.spinner("All entries analyzed. Generating insights..."):
        reflection_manager = get_reflection_manager(st.session_state.user_id)
        reflection_manager.delete_all_reflections_without_answer()
        journal_manager = get_journal_manager(st.session_state.user_id)
        report_analysis = journal_manager.save_journal_entry()
    if report_analysis:
        render_final_analysis()
        
        if not reflection_manager.original_entry_id:
            return
        original_entry = reflection_manager.get_reflection_by_id(reflection_manager.original_entry_id)
        if original_entry:
            question_manager = get_question_manager()
            question_manager.delete_question(original_entry.question)
    else:
        st.error("Final analysis not generated")
    return


def render_final_analysis():
    journal_manager = get_journal_manager(st.session_state.user_id)
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
    return


def main():
    # Get the journal manager and stats
    reflection_manager = get_reflection_manager(st.session_state.user_id)
    analyzed_entries, total_entries = reflection_manager.get_statistics()

    # Display the sidebar
    st.sidebar.title("Reflection Journal")
    st.sidebar.caption("Analyze and save your reflections")
    metric_col1, metric_col2 = st.sidebar.columns(2)    
    st.sidebar.button("Go to unanswered question", 
                      on_click=get_unanswered_reflection_entry,
                      use_container_width=True,
                      type="primary")
    st.sidebar.button("Skip to final analysis",
                      on_click=get_final_analysis,
                      use_container_width=True,
                      disabled=analyzed_entries == 0)

    # Generate insights
    if analyzed_entries == total_entries and analyzed_entries > 0:
        get_final_analysis()
        analyzed_entries, total_entries = reflection_manager.get_statistics()
        metric_col1.metric(label="Entries Analyzed", value=analyzed_entries)
        metric_col2.metric(label="Total Entries", value=total_entries)
        st.sidebar.info(f"{analyzed_entries} entries saved")
        render_final_analysis()
        return

    # Initialize the reflection entries
    if total_entries == 0:
        question_manager = get_question_manager()
        question = question_manager.get_random_question_entry()
        original_entry_id = reflection_manager.upsert_reflection(question)
        set_current_entry(original_entry_id)

    # Display the current entry
    current_entry = reflection_manager.get_reflection_by_id(st.session_state.current_entry_id)
    if not current_entry:
        st.warning("Current entry not found, going back to original entry")
        if reflection_manager.original_entry_id:
            set_current_entry(reflection_manager.original_entry_id)
            current_entry = reflection_manager.get_reflection_by_id(st.session_state.current_entry_id)
        else:
            st.error("Original entry not found")
            st.stop()

    # Render the current entry and its children
    if current_entry:
        render_entry(current_entry.id)
        for child in current_entry.children_ids:
            render_entry(child, is_child=True)

    # Update and display the metrics
    analyzed_entries, total_entries = reflection_manager.get_statistics()
    metric_col1.metric(label="Entries Analyzed", value=analyzed_entries)
    metric_col2.metric(label="Total Entries", value=total_entries)

    
if __name__ == "__main__":
    st.session_state.user_id = "default"
    main()
