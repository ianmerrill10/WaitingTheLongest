"""
Waiting The Longest™ - Webhooks
================================
Webhook delivery and management.
"""

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import httpx


logger = logging.getLogger(__name__)


# =============================================================================
# Webhook Events
# =============================================================================

class WebhookEvent(str, Enum):
    """Types of webhook events."""
    
    # Animal events
    ANIMAL_CREATED = "animal.created"
    ANIMAL_UPDATED = "animal.updated"
    ANIMAL_ADOPTED = "animal.adopted"
    ANIMAL_DELETED = "animal.deleted"
    
    # Shelter events
    SHELTER_CREATED = "shelter.created"
    SHELTER_UPDATED = "shelter.updated"
    
    # Newsletter events
    NEWSLETTER_SUBSCRIBED = "newsletter.subscribed"
    NEWSLETTER_UNSUBSCRIBED = "newsletter.unsubscribed"
    
    # Donation events
    DONATION_RECEIVED = "donation.received"
    
    # System events
    INGEST_COMPLETED = "ingest.completed"
    INGEST_FAILED = "ingest.failed"


# =============================================================================
# Webhook Configuration
# =============================================================================

@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""
    
    id: str
    url: str
    secret: str
    events: list[WebhookEvent] = field(default_factory=list)
    enabled: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    timeout_seconds: float = 30.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    
    def should_receive(self, event: WebhookEvent) -> bool:
        """Check if this webhook should receive an event."""
        if not self.enabled:
            return False
        
        # Empty events list means receive all
        if not self.events:
            return True
        
        return event in self.events


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""
    
    id: str
    webhook_id: str
    event: WebhookEvent
    payload: dict
    
    # Delivery status
    status: str = "pending"  # pending, success, failed
    attempts: int = 0
    last_attempt: datetime | None = None
    
    # Response info
    response_status: int | None = None
    response_body: str | None = None
    error: str | None = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: datetime | None = None


# =============================================================================
# Webhook Manager
# =============================================================================

class WebhookManager:
    """
    Manages webhook subscriptions and deliveries.
    """
    
    def __init__(self):
        self.webhooks: dict[str, WebhookConfig] = {}
        self.deliveries: list[WebhookDelivery] = []
    
    def register(self, config: WebhookConfig) -> WebhookConfig:
        """Register a new webhook."""
        self.webhooks[config.id] = config
        logger.info(f"Registered webhook: {config.id} -> {config.url}")
        return config
    
    def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")
            return True
        return False
    
    def get(self, webhook_id: str) -> WebhookConfig | None:
        """Get webhook by ID."""
        return self.webhooks.get(webhook_id)
    
    def list_webhooks(self) -> list[WebhookConfig]:
        """List all registered webhooks."""
        return list(self.webhooks.values())
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC signature for payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
    
    def _create_delivery(
        self,
        webhook: WebhookConfig,
        event: WebhookEvent,
        data: dict,
    ) -> WebhookDelivery:
        """Create a delivery record."""
        delivery_id = f"del_{int(time.time() * 1000)}_{webhook.id}"
        
        return WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event=event,
            payload={
                "event": event.value,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            },
        )
    
    async def deliver(
        self,
        delivery: WebhookDelivery,
        webhook: WebhookConfig,
    ) -> bool:
        """Attempt to deliver a webhook."""
        delivery.attempts += 1
        delivery.last_attempt = datetime.utcnow()
        
        payload_json = json.dumps(delivery.payload)
        signature = self._sign_payload(payload_json, webhook.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event.value,
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Delivery": delivery.id,
            "User-Agent": "WaitingTheLongest-Webhook/1.0",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers,
                    timeout=webhook.timeout_seconds,
                )
            
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Limit stored response
            
            if 200 <= response.status_code < 300:
                delivery.status = "success"
                delivery.delivered_at = datetime.utcnow()
                logger.info(f"Webhook delivered: {delivery.id}")
                return True
            else:
                delivery.error = f"HTTP {response.status_code}"
                logger.warning(f"Webhook failed: {delivery.id} - {delivery.error}")
                
        except httpx.TimeoutException:
            delivery.error = "Timeout"
            logger.warning(f"Webhook timeout: {delivery.id}")
            
        except Exception as e:
            delivery.error = str(e)
            logger.exception(f"Webhook error: {delivery.id}")
        
        # Retry if attempts remain
        if delivery.attempts < webhook.max_retries:
            delivery.status = "pending"
        else:
            delivery.status = "failed"
        
        return False
    
    async def emit(
        self,
        event: WebhookEvent,
        data: dict,
    ):
        """
        Emit an event to all relevant webhooks.
        
        Args:
            event: The event type
            data: Event payload data
        """
        # Find webhooks that should receive this event
        webhooks = [w for w in self.webhooks.values() if w.should_receive(event)]
        
        if not webhooks:
            return
        
        logger.info(f"Emitting {event.value} to {len(webhooks)} webhooks")
        
        for webhook in webhooks:
            delivery = self._create_delivery(webhook, event, data)
            self.deliveries.append(delivery)
            
            # Attempt delivery
            success = await self.deliver(delivery, webhook)
            
            # Retry if needed
            while not success and delivery.status == "pending":
                await asyncio.sleep(webhook.retry_delay_seconds)
                success = await self.deliver(delivery, webhook)
    
    def get_deliveries(
        self,
        webhook_id: str | None = None,
        event: WebhookEvent | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Get delivery history with optional filters."""
        filtered = self.deliveries
        
        if webhook_id:
            filtered = [d for d in filtered if d.webhook_id == webhook_id]
        
        if event:
            filtered = [d for d in filtered if d.event == event]
        
        if status:
            filtered = [d for d in filtered if d.status == status]
        
        # Sort by created_at descending
        filtered.sort(key=lambda d: d.created_at, reverse=True)
        
        return filtered[:limit]


# =============================================================================
# Global Instance
# =============================================================================

_webhook_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


# =============================================================================
# Convenience Functions
# =============================================================================

import asyncio


async def emit_webhook(event: WebhookEvent, data: dict):
    """Emit a webhook event."""
    manager = get_webhook_manager()
    await manager.emit(event, data)


def emit_webhook_sync(event: WebhookEvent, data: dict):
    """Emit a webhook event (sync wrapper)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(emit_webhook(event, data))
        else:
            loop.run_until_complete(emit_webhook(event, data))
    except RuntimeError:
        # No event loop, create one
        asyncio.run(emit_webhook(event, data))


# =============================================================================
# Event Emitters (for integration)
# =============================================================================

async def on_animal_created(animal_data: dict):
    """Emit animal created event."""
    await emit_webhook(WebhookEvent.ANIMAL_CREATED, animal_data)


async def on_animal_adopted(animal_id: int, adopter_info: dict | None = None):
    """Emit animal adopted event."""
    await emit_webhook(
        WebhookEvent.ANIMAL_ADOPTED,
        {"animal_id": animal_id, "adopter": adopter_info},
    )


async def on_ingest_completed(source: str, count: int):
    """Emit ingest completed event."""
    await emit_webhook(
        WebhookEvent.INGEST_COMPLETED,
        {"source": source, "animals_processed": count},
    )


async def on_donation_received(amount: float, donor_info: dict | None = None):
    """Emit donation received event."""
    await emit_webhook(
        WebhookEvent.DONATION_RECEIVED,
        {"amount": amount, "donor": donor_info},
    )
