"""Messaging platform adapters (Telegram, Discord, etc.)."""

from .base import CLISession, MessagingPlatform, SessionManagerInterface
from .factory import create_messaging_platform, create_messaging_platforms

__all__ = [
    "CLISession",
    "MessagingPlatform",
    "SessionManagerInterface",
    "create_messaging_platform",
    "create_messaging_platforms",
]
