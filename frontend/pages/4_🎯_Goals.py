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


def get_status_display(status):
    """Get emoji and text for status"""
    status_map = {
        'not_started': ('🔵', 'Not Started'),
        'in_progress': ('🟡', 'In Progress'),
        'completed': ('✅', 'Completed'),
        'abandoned': ('⚫', 'Abandoned')
    }
    return status_map.get(status, ('❓', status.replace('_', ' ').title()))


def get_confidence_display(confidence):
    """Get emoji and text for confidence level"""
    if not confidence:
        return None
    confidence_map = {
        'very_confident': ('💪', 'Very Confident'),
        'confident': ('👍', 'Confident'),
        'moderately_confident': ('🤞', 'Moderately Confident'),
        'slightly_confident': ('🤔', 'Slightly Confident'),
        'not_confident': ('😰', 'Not Confident')
    }
    return confidence_map.get(confidence, ('❓', confidence.replace('_', ' ').title()))


def render_goal_card(goal):
    """Render a single goal card"""
    with st.container():
        # Goal title and description
        st.markdown(f"### {goal['title']}")
        if goal.get('description'):
            st.markdown(f"*{goal['description']}*")

        # Status
        status_emoji, status_text = get_status_display(goal.get('status', 'not_started'))
        if goal.get('status') == 'completed':
            st.success(f"{status_emoji} {status_text}")
        elif goal.get('status') == 'abandoned':
            st.error(f"{status_emoji} {status_text}")
        elif goal.get('status') == 'in_progress':
            st.info(f"{status_emoji} {status_text}")
        else:
            st.info(f"{status_emoji} {status_text}")

        # Progress bar for metric goals
        if goal['goal_type'] == 'metric':
            target = goal.get('target_value', 0)
            current = goal.get('current_value', 0)
            unit = goal.get('unit', '')

            if target and target > 0:
                progress = min(current / target, 1.0)
                percentage = int(progress * 100)

                st.progress(progress)
                st.caption(f"Progress: {current}/{target} {unit} ({percentage}%)")
            else:
                st.caption(f"Current: {current} {unit}")

        # Confidence level
        if goal.get('current_confidence'):
            conf_emoji, conf_text = get_confidence_display(goal['current_confidence'])
            st.caption(f"Confidence: {conf_emoji} {conf_text}")

        # Justification
        if goal.get('justification'):
            st.caption(f"**Why this matters:** {goal['justification']}")

        # Deadline
        if goal.get('deadline'):
            deadline_text = format_deadline(goal['deadline'])
            st.caption(deadline_text)

        # Metadata
        st.caption(f"Type: {goal['goal_type'].capitalize()} • Priority: {goal.get('priority', 1000)} • Created: {datetime.fromisoformat(goal['created_at'].replace('Z', '+00:00')).strftime('%b %d, %Y')}")

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

        # Sort goals: by priority (ascending), then by status (active first), then by deadline
        status_priority = {
            'in_progress': 0,
            'not_started': 1,
            'completed': 2,
            'abandoned': 3
        }
        goals_sorted = sorted(
            goals,
            key=lambda g: (
                g.get('priority', 1000),
                status_priority.get(g.get('status', 'not_started'), 4),
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
