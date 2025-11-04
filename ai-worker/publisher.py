import json
from typing import Optional, List
from google.cloud import pubsub_v1
from models import Belief
from config import settings, logger


def publish_follow_up_questions(parent_id: str, beliefs: List[Belief]):
    for b in beliefs:
        data = {
            "message_type": "follow_up_question",
            "parent_id": parent_id,
            "question": b.challenge_question,
            "context": b.statement
        }
        message_id = publish_message(json.dumps(data).encode("utf-8"))
        if not message_id:
            logger.warning(f"The following data wasn't sent: {data}")
    return


def publish_message(message_data: bytes) -> Optional[str]:
    """
    Publishes a message to a Google Cloud Pub/Sub topic.
    message_data: The message to publish (in bytes)
    Returns: The message ID of the published message or None if publishing fails
    """

    try:
        # Initialize the Pub/Sub publisher client
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(
            settings.GOOGLE_CLOUD_PROJECT_ID, 
            settings.PUB_SUB_TOPIC_ID
        )
        
        # Publish the message
        future = publisher.publish(topic_path, message_data)
        message_id = future.result()
    except Exception as e:
        logger.warning(f"The follow up question was not published {e}")
        message_id = None
    return message_id
