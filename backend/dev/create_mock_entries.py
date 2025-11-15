#!/usr/bin/env python3
"""
Mock data generation script for testing the dashboard.

Creates ~15 entries across the last 30 days with varying sentiments,
multiple entries on some days, each containing a question and an answer.

Usage:
    python create_mock_entries.py [email]
    python create_mock_entries.py test@example.com
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, select

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Settings
from models import Reflection, SentimentType, User

# Mock data for entries - varying sentiments and content across 30 days
MOCK_ENTRIES = [
    # 30 days ago
    {
        "days_ago": 30,
        "sentiment": SentimentType.NEUTRAL,
        "question": "How did the project kickoff go?",
        "answer": "Project kickoff meeting was productive. Got clarity on requirements and timelines. Looking forward to getting started on implementation."
    },
    # 27 days ago
    {
        "days_ago": 27,
        "sentiment": SentimentType.POSITIVE,
        "question": "What achievements am I proud of?",
        "answer": "Successfully delivered the initial prototype ahead of schedule. The team was impressed with the quality and attention to detail."
    },
    {
        "days_ago": 27,
        "sentiment": SentimentType.NEGATIVE,
        "question": "What setbacks did I experience?",
        "answer": "Ran into unexpected compatibility issues with the database. Had to rollback some changes and take a different approach."
    },
    # 23 days ago
    {
        "days_ago": 23,
        "sentiment": SentimentType.POSITIVE,
        "question": "What went well in the sprint?",
        "answer": "Great sprint review! Delivered all planned features on time. Got excellent feedback from stakeholders about the UI improvements."
    },
    # 20 days ago
    {
        "days_ago": 20,
        "sentiment": SentimentType.NEUTRAL,
        "question": "How am I managing my workload?",
        "answer": "Workload is steady but manageable. Had to prioritize some tasks and defer others, but overall maintaining a good balance."
    },
    {
        "days_ago": 20,
        "sentiment": SentimentType.POSITIVE,
        "question": "What skills did I develop?",
        "answer": "Deepened my understanding of system architecture and microservices design patterns. This will help in future projects."
    },
    # 16 days ago
    {
        "days_ago": 16,
        "sentiment": SentimentType.NEGATIVE,
        "question": "What frustrated me this week?",
        "answer": "Code review feedback was more critical than expected. Some of my implementations weren't following team best practices. Need to study more."
    },
    # 13 days ago
    {
        "days_ago": 13,
        "sentiment": SentimentType.POSITIVE,
        "question": "What made me feel accomplished?",
        "answer": "Fixed a long-standing bug that was affecting user experience. The fix was elegant and the users are happy with the improvement."
    },
    {
        "days_ago": 13,
        "sentiment": SentimentType.NEUTRAL,
        "question": "How did the team collaborate?",
        "answer": "Had a good pair programming session. Learned a lot from my colleague's approach to problem-solving. Great synergy overall."
    },
    # 9 days ago
    {
        "days_ago": 9,
        "sentiment": SentimentType.NEUTRAL,
        "question": "What challenges came up?",
        "answer": "Faced some issues with third-party API rate limiting. Implemented a caching solution that should help mitigate this in the future."
    },
    # 6 days ago
    {
        "days_ago": 6,
        "sentiment": SentimentType.POSITIVE,
        "question": "What went well today?",
        "answer": "Had a great productive day! Completed the project milestone and received positive feedback from the team."
    },
    {
        "days_ago": 6,
        "sentiment": SentimentType.POSITIVE,
        "question": "What did I learn from today?",
        "answer": "Realized that taking breaks improves my productivity. Feeling more energized and creative after implementing this."
    },
    # 3 days ago
    {
        "days_ago": 3,
        "sentiment": SentimentType.NEGATIVE,
        "question": "How did the deployment go?",
        "answer": "Deployment had some hiccups with database migrations. Spent extra time debugging production issues but eventually got everything stable."
    },
    # 1 day ago
    {
        "days_ago": 1,
        "sentiment": SentimentType.NEUTRAL,
        "question": "What are my goals for this week?",
        "answer": "Planning to focus on code refactoring and technical debt. Also want to improve test coverage and documentation."
    },
    # Today
    {
        "days_ago": 0,
        "sentiment": SentimentType.POSITIVE,
        "question": "What am I grateful for?",
        "answer": "Grateful for supportive teammates, interesting work, and the opportunity to grow professionally. Feeling optimistic about the project."
    },
]


def create_mock_entries(user_email: str):
    """Create mock entries for a user."""
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

    with Session(engine) as session:
        # Find the user
        user = session.exec(select(User).where(User.email == user_email)).first()

        if not user:
            print(f"❌ User with email '{user_email}' not found.")
            return False

        print(f"👤 Creating mock entries for: {user.name} ({user.email})")
        print(f"📝 Creating {len(MOCK_ENTRIES)} entries (last 30 days)...")
        print()

        try:
            for i, entry_data in enumerate(MOCK_ENTRIES):
                # Calculate the date for this entry
                created_at = datetime.now() - timedelta(days=entry_data["days_ago"])

                # Create the reflection
                reflection = Reflection(
                    user_id=user.id,
                    created_at=created_at,
                    sentiment=entry_data["sentiment"],
                    question=entry_data["question"],
                    answer=entry_data["answer"]
                )

                session.add(reflection)
                session.commit()

                # Print entry info
                day_label = "Today" if entry_data["days_ago"] == 0 else f"{entry_data['days_ago']} days ago"
                print(f"✅ Entry {i+1}/{len(MOCK_ENTRIES)} ({day_label}) - {entry_data['sentiment']}")
                print(f"   📌 Q: {entry_data['question']}")
                print(f"   💭 A: {entry_data['answer'][:80]}...")
                print()

            print("✨ All mock entries created successfully!")
            print(f"📊 Total entries created: {len(MOCK_ENTRIES)}")
            return True

        except Exception as e:
            print(f"❌ Failed to create mock entries: {e}")
            session.rollback()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Create mock journal entries for dashboard testing",
        epilog="Example: python create_mock_entries.py test@example.com",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("email", help="Email of the user to create entries for")

    args = parser.parse_args()

    print("🚀 Creating Mock Journal Entries")
    print("=" * 50)

    success = create_mock_entries(args.email)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
