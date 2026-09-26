"""
Módulo de Webhooks
Sistema de notificações via webhooks para Discord e outros serviços
"""

from .discord_webhook import DiscordWebhook
from .manager import WebhooksManager
from .discord_bot_provisioner import DiscordBotProvisioner

__all__ = ["DiscordWebhook", "WebhooksManager", "DiscordBotProvisioner"]
