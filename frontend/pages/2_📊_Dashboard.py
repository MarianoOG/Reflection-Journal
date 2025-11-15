import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import sentiment_emojis, get_dashboard_stats, get_sentiment_by_date
from footer import render_sidebar_footer

def create_sentiment_chart(sentiment_data):
    """Create a sentiment chart with emoji labels"""
    if not sentiment_data:
        return None

    # Convert to DataFrame for easier handling
    df = pd.DataFrame(sentiment_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Set date as index for Streamlit line chart
    df = df.set_index('date')

    return df

def get_sentiment_emoji_label(value):
    """Convert sentiment value to emoji label using sentiment_emojis struct"""
    if value >= 0.33:
        return sentiment_emojis["Positive"]
    elif value <= -0.33:
        return sentiment_emojis["Negative"]
    else:
        return sentiment_emojis["Neutral"]

def main():
    st.title("📊 Dashboard")
    st.markdown("Get insights into your reflection journey")

    # Fetch data
    stats = get_dashboard_stats()
    sentiment_data = get_sentiment_by_date()

    if not stats:
        st.error("Failed to load dashboard statistics")
        render_sidebar_footer()
        return

    if not sentiment_data:
        st.error("Failed to load sentiment data")
        render_sidebar_footer()
        return

    # Use a centered container with max width
    # Calculate entries per week, activity percentage, and average entries per day
    entries_per_week = 0
    activity_percentage = 0
    avg_entries_per_day = 0
    sentiment_list = sentiment_data.get("sentiment_data", [])

    if sentiment_list:
        # Calculate entries per week (average of last 30 days)
        total_entries_last_month = sum(item.get('entries_count', 0) for item in sentiment_list)
        weeks_in_month = 4.28571  # Average weeks in a month (30 days / 7)
        entries_per_week = total_entries_last_month / weeks_in_month

        # Calculate activity percentage (days with at least 1 entry / days in month)
        from datetime import datetime
        dates = [datetime.strptime(item['date'], '%Y-%m-%d').date() for item in sentiment_list]
        if dates:
            start_date = min(dates)
            end_date = max(dates)
            total_days_in_range = (end_date - start_date).days + 1
            days_with_entries = len(sentiment_list)
            activity_percentage = (days_with_entries / total_days_in_range) * 100

            # Calculate average entries per day (on days with entries)
            if days_with_entries > 0:
                avg_entries_per_day = total_entries_last_month / days_with_entries

    with st.container():
        # Combined Quick Insights & Statistics Section
        st.divider()
        st.subheader("💡 Quick Insights & Statistics")

        if stats.get("total_entries", 0) == 0:
            st.info("Start journaling to see insights about your reflections!")
        else:
            # First row: Core statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label="Total Entries",
                    value=stats.get("total_entries", 0),
                    help="Total number of reflections you've created"
                )
            with col2:
                st.metric(
                    label="Answered",
                    value=stats.get("entries_with_answers", 0),
                    help="Number of reflections with answers"
                )
            with col3:
                st.metric(
                    label="Follow-ups",
                    value=stats.get("follow_up_questions_without_answers", 0),
                    help="Number of unanswered follow-up questions"
                )


        st.divider()

        # Activity Analytics Section
        st.subheader("📈 Activity Analytics")

        if sentiment_data.get("has_sufficient_data"):
            sentiment_list = sentiment_data.get("sentiment_data", [])

            if sentiment_list:
                # Create line chart for entries per day
                chart_df = create_sentiment_chart(sentiment_list)
                if chart_df is not None:
                    # Create Plotly figure for entries count
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=chart_df.index,
                        y=chart_df['entries_count'],
                        mode='lines+markers',
                        name='Daily Entries',
                        line=dict(color='#0B5FCC', width=3),
                        marker=dict(size=8),
                        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Entries: %{y}<extra></extra>'
                    ))

                    fig.update_layout(
                        height=350,
                        hovermode='x unified',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        margin=dict(l=50, r=50, t=20, b=50),
                        yaxis=dict(
                            title='Number of Entries',
                            gridcolor='rgba(200,200,200,0.2)',
                            showgrid=True,
                        ),
                        xaxis=dict(
                            title='Date',
                            gridcolor='rgba(200,200,200,0)',
                            showgrid=False,
                        ),
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Display metrics below the chart
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            label="Entries per Week",
                            value=f"{entries_per_week:.1f}",
                            help="Average number of entries per week (last 30 days)"
                        )
                    with col2:
                        st.metric(
                            label="Avg per Active Day",
                            value=f"{avg_entries_per_day:.1f}",
                            help="Average entries per day (only counting active days)"
                        )
                    with col3:
                        st.metric(
                            label="Activity %",
                            value=f"{activity_percentage:.1f}%",
                            help="Percentage of days with at least 1 entry"
                        )
        else:
            st.info("📝 Need more data to display activity analytics")

        st.divider()

        # Sentiment Chart Section
        st.subheader("💭 Sentiment Trend")

        if sentiment_data.get("has_sufficient_data"):
            # Display chart
            sentiment_list = sentiment_data.get("sentiment_data", [])

            if sentiment_list:
                chart_df = create_sentiment_chart(sentiment_list)
                if chart_df is not None:
                    # Create Plotly figure with emoji y-axis labels
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=chart_df.index,
                        y=chart_df['sentiment_value'],
                        mode='lines+markers',
                        name='Sentiment',
                        line=dict(color='#FF9500', width=3),
                        marker=dict(size=8),
                        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Sentiment: %{y:.2f}<extra></extra>'
                    ))

                    fig.update_layout(
                        height=450,
                        hovermode='x unified',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        margin=dict(l=50, r=50, t=20, b=50),
                        yaxis=dict(
                            range=[-1, 1],
                            tickvals=[-1, 0, 1],
                            ticktext=[sentiment_emojis["Negative"], sentiment_emojis["Neutral"], sentiment_emojis["Positive"]],
                            gridcolor='rgba(200,200,200,0.2)',
                            showgrid=True,
                        ),
                        xaxis=dict(
                            gridcolor='rgba(200,200,200,0)',
                            showgrid=False,
                        ),
                    )

                    st.plotly_chart(fig, width='stretch')

                    # Show sentiment breakdown for the period
                    sentiment_values = [item['sentiment_value'] for item in sentiment_list]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        positive_count = sum(1 for v in sentiment_values if v >= 0.33)
                        st.metric(f"{sentiment_emojis['Positive']} Positive Days", positive_count)
                    with col2:
                        neutral_count = sum(1 for v in sentiment_values if -0.33 <= v < 0.33)
                        st.metric(f"{sentiment_emojis['Neutral']} Neutral Days", neutral_count)
                    with col3:
                        negative_count = sum(1 for v in sentiment_values if v < -0.33)
                        st.metric(f"{sentiment_emojis['Negative']} Negative Days", negative_count)
                else:
                    st.warning("Could not generate sentiment chart")
            else:
                st.info("No sentiment data available")
        else:
            # Show info message
            st.info(
                "📝 **Need more data**\n\n"
                "To display sentiment trends, you need entries on at least 5 different days in the last month. "
                f"Currently: {len(sentiment_data.get('sentiment_data', []))} day(s) with entries."
            )

    # Render footer
    render_sidebar_footer()

if __name__ == "__main__":
    st.set_page_config(layout="centered", page_icon="📊", page_title="Dashboard")
    if "access_token" not in st.session_state:
        st.switch_page("🏠_Home.py")
    st.session_state["Page"] = "Dashboard"
    main()
