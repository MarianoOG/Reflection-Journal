import streamlit as st
from datetime import datetime
from utils import api_request
from footer import render_sidebar_footer


def format_deadline(deadline_str):
    """Format deadline string to a readable format"""
    if not deadline_str:
        return "No deadline"

    try:
        deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
        today = datetime.now(deadline.tzinfo)
        days_until = (deadline - today).days

        formatted_date = deadline.strftime("%b %d, %Y")

        if days_until < 0:
            return f"⚠️ {formatted_date} (Overdue)"
        elif days_until == 0:
            return f"⏰ {formatted_date} (Today)"
        elif days_until <= 7:
            return f"⏰ {formatted_date} ({days_until} days left)"
        else:
            return f"📅 {formatted_date}"
    except:
        return deadline_str


def render_goal_card(goal):
    """Render a single goal card"""
    with st.container():
        # Goal title and description
        st.markdown(f"### {goal['title']}")
        if goal.get('description'):
            st.markdown(f"*{goal['description']}*")

        # Goal type and status
        col1, col2 = st.columns([2, 1])

        with col1:
            if goal['goal_type'] == 'boolean':
                # Boolean goal - show completion status
                if goal['is_completed']:
                    st.success("✅ Completed")
                else:
                    st.info("⏳ In Progress")
            else:
                # Metric goal - show progress bar
                target = goal.get('target_value', 0)
                current = goal.get('current_value', 0)
                unit = goal.get('unit', '')

                if target > 0:
                    progress = min(current / target, 1.0)
                    percentage = int(progress * 100)

                    st.progress(progress)
                    st.caption(f"Progress: {current}/{target} {unit} ({percentage}%)")
                else:
                    st.caption(f"Current: {current} {unit}")

        with col2:
            # Deadline
            if goal.get('deadline'):
                deadline_text = format_deadline(goal['deadline'])
                st.caption(deadline_text)

        # Metadata
        st.caption(f"Type: {goal['goal_type'].capitalize()} • Created: {datetime.fromisoformat(goal['created_at'].replace('Z', '+00:00')).strftime('%b %d, %Y')}")

        st.divider()


def main():
    st.title("🎯 Goals")
    st.markdown("Track your SMART goals and progress")

    # Fetch goals from backend
    goals = api_request("GET", "/goals/")

    if goals is None:
        st.error("Failed to load goals")
        render_sidebar_footer()
        return

    # Display goals
    if len(goals) == 0:
        st.info("🎯 You haven't set any goals yet. Start by adding your first goal!")
    else:
        st.markdown(f"**You have {len(goals)} goal(s)** (maximum 5)")
        st.divider()

        # Sort goals: incomplete first, then by deadline
        goals_sorted = sorted(
            goals,
            key=lambda g: (
                g.get('is_completed', False) if g['goal_type'] == 'boolean' else False,
                g.get('deadline') or '9999-12-31'
            )
        )

        for goal in goals_sorted:
            render_goal_card(goal)

    # Render footer
    render_sidebar_footer()


if __name__ == "__main__":
    st.set_page_config(layout="centered", page_icon="🎯", page_title="Goals")
    if "access_token" not in st.session_state:
        st.switch_page("🏠_Home.py")
    st.session_state["Page"] = "Goals"
    main()
