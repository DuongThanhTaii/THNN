"""Tests for messaging platform factory."""

from unittest.mock import MagicMock, patch

from messaging.platforms.factory import (
    create_messaging_platform,
    create_messaging_platforms,
)


class TestCreateMessagingPlatform:
    """Tests for create_messaging_platform factory function."""

    def test_telegram_with_token(self):
        """Create Telegram platform when bot_token is provided."""
        mock_platform = MagicMock()
        with (
            patch("messaging.platforms.telegram.TELEGRAM_AVAILABLE", True),
            patch(
                "messaging.platforms.telegram.TelegramPlatform",
                return_value=mock_platform,
            ),
        ):
            result = create_messaging_platform(
                "telegram",
                bot_token="test_token",
                allowed_user_id="12345",
            )

        assert result is mock_platform

    def test_telegram_without_token(self):
        """Return None when no bot_token for Telegram."""
        result = create_messaging_platform("telegram")
        assert result is None

    def test_telegram_empty_token(self):
        """Return None when bot_token is empty string."""
        result = create_messaging_platform("telegram", bot_token="")
        assert result is None

    def test_discord_with_token(self):
        """Create Discord platform when discord_bot_token is provided."""
        mock_platform = MagicMock()
        with (
            patch("messaging.platforms.discord.DISCORD_AVAILABLE", True),
            patch(
                "messaging.platforms.discord.DiscordPlatform",
                return_value=mock_platform,
            ),
        ):
            result = create_messaging_platform(
                "discord",
                discord_bot_token="test_token",
                allowed_discord_channels="123,456",
            )

        assert result is mock_platform

    def test_discord_without_token(self):
        """Return None when no discord_bot_token for Discord."""
        result = create_messaging_platform("discord")
        assert result is None

    def test_discord_empty_token(self):
        """Return None when discord_bot_token is empty string."""
        result = create_messaging_platform(
            "discord", discord_bot_token="", allowed_discord_channels="123"
        )
        assert result is None

    def test_web_platform_creation(self):
        """Create web adapter without external token dependencies."""
        result = create_messaging_platform("web", web_workspace_id=7)
        assert result is not None
        assert result.name == "web"

    def test_esp32_platform_creation(self):
        """Create ESP32 adapter when channel is enabled and broker is configured."""
        mock_platform = MagicMock()
        with patch(
            "messaging.platforms.esp32.Esp32MqttPlatform",
            return_value=mock_platform,
        ):
            result = create_messaging_platform(
                "esp32",
                enable_esp32=True,
                esp32_mqtt_broker_url="mqtts://broker.example.com:8883",
                esp32_mqtt_topic_prefix="agent",
            )

        assert result is mock_platform

    def test_esp32_platform_disabled(self):
        """Return None when ESP32 channel is disabled."""
        result = create_messaging_platform(
            "esp32",
            enable_esp32=False,
            esp32_mqtt_broker_url="mqtts://broker.example.com:8883",
        )
        assert result is None

    def test_esp32_platform_missing_broker(self):
        """Return None when ESP32 broker URL is missing."""
        result = create_messaging_platform("esp32", enable_esp32=True)
        assert result is None

    def test_unknown_platform(self):
        """Return None for unknown platform types."""
        result = create_messaging_platform("slack")
        assert result is None

    def test_unknown_platform_with_kwargs(self):
        """Return None for unknown platform even with kwargs."""
        result = create_messaging_platform("slack", bot_token="token")
        assert result is None


class TestCreateMessagingPlatforms:
    """Tests for create_messaging_platforms helper."""

    def test_comma_separated_platforms_create_multiple(self):
        telegram_platform = MagicMock(name="telegram")
        discord_platform = MagicMock(name="discord")

        with patch(
            "messaging.platforms.factory.create_messaging_platform",
            side_effect=[telegram_platform, discord_platform],
        ) as create_single:
            result = create_messaging_platforms(
                "telegram,discord",
                bot_token="t",
                discord_bot_token="d",
            )

        assert result == [telegram_platform, discord_platform]
        assert create_single.call_count == 2

    def test_skips_empty_and_duplicate_platform_names(self):
        telegram_platform = MagicMock(name="telegram")

        with patch(
            "messaging.platforms.factory.create_messaging_platform",
            return_value=telegram_platform,
        ) as create_single:
            result = create_messaging_platforms(" telegram ,, TELEGRAM ", bot_token="t")

        assert result == [telegram_platform]
        create_single.assert_called_once_with(platform_type="telegram", bot_token="t")

    def test_skips_unconfigured_platform_instances(self):
        discord_platform = MagicMock(name="discord")

        with patch(
            "messaging.platforms.factory.create_messaging_platform",
            side_effect=[None, discord_platform],
        ):
            result = create_messaging_platforms(
                ["telegram", "discord"],
                bot_token="",
                discord_bot_token="d",
            )

        assert result == [discord_platform]
