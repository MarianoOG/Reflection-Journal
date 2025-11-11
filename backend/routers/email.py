"""
Email router for sending feedback and notifications.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Settings, logger

settings = Settings()
router = APIRouter(prefix="/email", tags=["email"])


class FeedbackRequest(BaseModel):
    """Schema for feedback submission."""
    issue_type: str
    description: str
    session_info: dict = {}


@router.post("/send-feedback", status_code=status.HTTP_200_OK)
async def send_feedback(feedback: FeedbackRequest) -> dict:
    """
    Send feedback via email.

    Args:
        feedback: FeedbackRequest containing issue type, description, and optional session info

    Returns:
        dict: Success message if email sent successfully

    Raises:
        HTTPException: 400 if email configuration is missing
        HTTPException: 500 if email sending fails
    """
    # Validate email configuration
    if not settings.SENDER_EMAIL or not settings.SENDER_PASSWORD or not settings.RECIPIENT_EMAIL:
        logger.error("Email configuration is incomplete - missing SENDER_EMAIL, SENDER_PASSWORD, or RECIPIENT_EMAIL")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email service is not properly configured"
        )

    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = settings.SENDER_EMAIL
        message["To"] = settings.RECIPIENT_EMAIL
        message["Subject"] = feedback.issue_type

        # Format session info
        session_info_text = ""
        if feedback.session_info:
            sorted_keys = sorted(feedback.session_info.keys())
            for key in sorted_keys:
                value = feedback.session_info[key]
                session_info_text += f"{key}: {value}\n"

        # Create email body
        email_body = f"""
Feedback Report
===============

Type: {feedback.issue_type}
Timestamp: {datetime.now().isoformat()}

Description:
{feedback.description}

---

Session Information:

{session_info_text}
        """

        message.attach(MIMEText(email_body, "plain"))

        # Send email via SMTP
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
            server.send_message(message)

        logger.info(f"Feedback email sent successfully for issue type: {feedback.issue_type}")
        return {"message": "Feedback submitted successfully"}

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authenticate with email service"
        )
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while sending email"
        )
