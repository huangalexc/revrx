"""
Email service using Resend API
Handles sending verification emails, password reset emails, etc.
"""

import structlog
from typing import Optional
import httpx

from app.core.config import settings


logger = structlog.get_logger(__name__)


class EmailService:
    """Email service for sending transactional emails"""

    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.FROM_EMAIL
        self.base_url = "https://api.resend.com"

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None
    ) -> bool:
        """
        Send an email using Resend API

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML email body
            text: Plain text email body (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": self.from_email,
                        "to": [to],
                        "subject": subject,
                        "html": html,
                        "text": text
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.info("Email sent successfully", to=to, subject=subject)
                    return True
                else:
                    logger.error(
                        "Failed to send email",
                        to=to,
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False

        except Exception as e:
            logger.error("Error sending email", to=to, error=str(e))
            return False

    async def send_verification_email(
        self,
        to: str,
        token: str,
        frontend_url: str = None
    ) -> bool:
        """
        Send email verification email

        Args:
            to: Recipient email address
            token: Verification token
            frontend_url: Frontend base URL

        Returns:
            True if email sent successfully
        """
        if frontend_url is None:
            frontend_url = settings.FRONTEND_URL
        verification_link = f"{frontend_url}/verify-email?token={token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">Verify Your Email</h1>
                <p>Thank you for registering with Post-Facto Coding Review!</p>
                <p>Please click the button below to verify your email address:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}"
                       style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verify Email
                    </a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #7f8c8d;">{verification_link}</p>
                <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
                    This link will expire in 24 hours. If you didn't request this email, please ignore it.
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        Verify Your Email

        Thank you for registering with Post-Facto Coding Review!

        Please visit the following link to verify your email address:
        {verification_link}

        This link will expire in 24 hours. If you didn't request this email, please ignore it.
        """

        return await self.send_email(
            to=to,
            subject="Verify Your Email - Post-Facto Coding Review",
            html=html,
            text=text
        )

    async def send_password_reset_email(
        self,
        to: str,
        token: str,
        frontend_url: str = None
    ) -> bool:
        """
        Send password reset email

        Args:
            to: Recipient email address
            token: Password reset token
            frontend_url: Frontend base URL

        Returns:
            True if email sent successfully
        """
        if frontend_url is None:
            frontend_url = settings.FRONTEND_URL
        reset_link = f"{frontend_url}/reset-password?token={token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">Reset Your Password</h1>
                <p>We received a request to reset your password for your Post-Facto Coding Review account.</p>
                <p>Click the button below to reset your password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}"
                       style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #7f8c8d;">{reset_link}</p>
                <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
                    This link will expire in 1 hour. If you didn't request this email, please ignore it and your password will remain unchanged.
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        Reset Your Password

        We received a request to reset your password for your Post-Facto Coding Review account.

        Please visit the following link to reset your password:
        {reset_link}

        This link will expire in 1 hour. If you didn't request this email, please ignore it.
        """

        return await self.send_email(
            to=to,
            subject="Reset Your Password - Post-Facto Coding Review",
            html=html,
            text=text
        )

    async def send_welcome_email(self, to: str, trial_days: int = 7) -> bool:
        """
        Send welcome email after email verification

        Args:
            to: Recipient email address
            trial_days: Number of trial days

        Returns:
            True if email sent successfully
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h1 style="color: #27ae60; margin-bottom: 20px;">Welcome to Post-Facto Coding Review!</h1>
                <p>Your email has been verified and your {trial_days}-day free trial has started.</p>
                <p>You can now:</p>
                <ul>
                    <li>Upload clinical notes for AI-powered coding review</li>
                    <li>Compare billed codes with AI suggestions</li>
                    <li>Discover potential revenue opportunities</li>
                    <li>Generate detailed coding reports</li>
                </ul>
                <p>Get started now by uploading your first clinical note!</p>
                <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
                    Your trial will expire in {trial_days} days. You can upgrade to a paid subscription at any time.
                </p>
            </div>
        </body>
        </html>
        """

        text = f"""
        Welcome to Post-Facto Coding Review!

        Your email has been verified and your {trial_days}-day free trial has started.

        You can now:
        - Upload clinical notes for AI-powered coding review
        - Compare billed codes with AI suggestions
        - Discover potential revenue opportunities
        - Generate detailed coding reports

        Get started now by uploading your first clinical note!

        Your trial will expire in {trial_days} days.
        """

        return await self.send_email(
            to=to,
            subject="Welcome to Post-Facto Coding Review!",
            html=html,
            text=text
        )


# Export singleton instance
email_service = EmailService()
