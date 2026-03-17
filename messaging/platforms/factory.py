"""Messaging platform factory.

Creates the appropriate messaging platform adapter based on configuration.
To add a new platform (e.g. Discord, Slack):
1. Create a new class implementing MessagingPlatform in messaging/platforms/
2. Add a case to create_messaging_platform() below
"""

from loguru import logger

from .base import MessagingPlatform


def _normalize_platform_types(platform_types: str | list[str]) -> list[str]:
    if isinstance(platform_types, str):
        raw_items = platform_types.split(",")
    else:
        raw_items = platform_types

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        name = item.strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def create_messaging_platform(
    platform_type: str,
    **kwargs,
) -> MessagingPlatform | None:
    """Create a messaging platform instance based on type.

    Args:
        platform_type: Platform identifier ("telegram", "discord", etc.)
        **kwargs: Platform-specific configuration passed to the constructor.

    Returns:
        Configured MessagingPlatform instance, or None if not configured.
    """
    if platform_type == "telegram":
        bot_token = kwargs.get("bot_token")
        if not bot_token:
            logger.info("No Telegram bot token configured, skipping platform setup")
            return None

        from .telegram import TelegramPlatform

        return TelegramPlatform(
            bot_token=bot_token,
            allowed_user_id=kwargs.get("allowed_user_id"),
        )

    if platform_type == "discord":
        bot_token = kwargs.get("discord_bot_token")
        if not bot_token:
            logger.info("No Discord bot token configured, skipping platform setup")
            return None

        from .discord import DiscordPlatform

        return DiscordPlatform(
            bot_token=bot_token,
            allowed_channel_ids=kwargs.get("allowed_discord_channels"),
        )

    if platform_type == "web":
        from .web import WebPlatform

        return WebPlatform(workspace_id=int(kwargs.get("web_workspace_id", 1)))

    if platform_type == "esp32":
        if not bool(kwargs.get("enable_esp32", False)):
            logger.info("ESP32 channel disabled, skipping platform setup")
            return None

        broker_url = kwargs.get("esp32_mqtt_broker_url")
        if not broker_url:
            logger.info("No ESP32 MQTT broker URL configured, skipping platform setup")
            return None

        from .esp32 import Esp32MqttPlatform

        return Esp32MqttPlatform(
            broker_url=str(broker_url),
            username=kwargs.get("esp32_mqtt_username"),
            password=kwargs.get("esp32_mqtt_password"),
            topic_prefix=str(kwargs.get("esp32_mqtt_topic_prefix", "agent")),
            device_shared_secret=kwargs.get("esp32_device_shared_secret"),
        )

    logger.warning(
        "Unknown messaging platform: "
        f"'{platform_type}'. Supported: 'telegram', 'discord', 'web', 'esp32'"
    )
    return None


def create_messaging_platforms(
    platform_types: str | list[str],
    **kwargs,
) -> list[MessagingPlatform]:
    """Create multiple configured messaging platforms.

    Accepts either a comma-separated string or a list of platform names.
    Unknown or unconfigured platforms are skipped.
    """

    platforms: list[MessagingPlatform] = []
    for platform_type in _normalize_platform_types(platform_types):
        platform = create_messaging_platform(platform_type=platform_type, **kwargs)
        if platform is not None:
            platforms.append(platform)
    return platforms
