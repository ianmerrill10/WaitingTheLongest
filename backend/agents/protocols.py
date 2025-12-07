#!/usr/bin/env python3
"""
===============================================================================
Agent Cooperation Protocol - Inter-Agent Communication & Data Sharing
===============================================================================
Defines the standardized protocols for agent-to-agent communication,
data sharing, and cooperative task execution.

CORE PRINCIPLES:
1. COOPERATION MANDATE: All agents MUST respond helpfully when asked by another agent
2. DATA SHARING: Agents share relevant data freely when it benefits the system
3. MUTUAL ASSISTANCE: Agents prioritize helping other agents complete their tasks
4. TRANSPARENT COMMUNICATION: All inter-agent communications are logged

Author: Waiting The Longest Development Team
===============================================================================
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import queue
import logging
import hashlib
import threading


class MessageType(Enum):
    """Types of inter-agent messages"""
    REQUEST = "request"           # Asking for help or data
    RESPONSE = "response"         # Responding to a request
    BROADCAST = "broadcast"       # Message to all agents
    NOTIFICATION = "notification" # Informational update
    DATA_SHARE = "data_share"     # Sharing data proactively
    ALERT = "alert"               # Urgent notification
    HANDOFF = "handoff"           # Transferring task to another agent
    ACK = "acknowledgment"        # Confirming receipt


class DataCategory(Enum):
    """Categories of shareable data"""
    SHELTER = "shelter"
    ANIMAL = "animal"
    CONTENT = "content"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    ERROR = "error"
    RESOURCE = "resource"
    SCHEDULE = "schedule"
    USER = "user"


class Priority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class AgentMessage:
    """
    Standard message format for inter-agent communication.

    All agents use this format to ensure consistent communication.
    """
    message_id: str
    from_agent: str
    to_agent: str  # Use "*" for broadcast
    message_type: MessageType
    subject: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    response_to: Optional[str] = None  # ID of message being responded to
    ttl_minutes: int = 60  # Time to live
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'message_id': self.message_id,
            'from_agent': self.from_agent,
            'to_agent': self.to_agent,
            'message_type': self.message_type.value,
            'subject': self.subject,
            'payload': self.payload,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'requires_response': self.requires_response,
            'response_to': self.response_to,
            'ttl_minutes': self.ttl_minutes,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentMessage':
        return cls(
            message_id=data['message_id'],
            from_agent=data['from_agent'],
            to_agent=data['to_agent'],
            message_type=MessageType(data['message_type']),
            subject=data['subject'],
            payload=data['payload'],
            priority=Priority(data['priority']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            requires_response=data.get('requires_response', False),
            response_to=data.get('response_to'),
            ttl_minutes=data.get('ttl_minutes', 60),
            metadata=data.get('metadata', {})
        )


@dataclass
class DataPackage:
    """
    Standard format for sharing data between agents.

    Agents use this to share discoveries, results, and resources.
    """
    package_id: str
    category: DataCategory
    source_agent: str
    title: str
    data: Any
    schema_version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_public: bool = True  # Available to all agents
    target_agents: List[str] = field(default_factory=list)  # Specific recipients
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'package_id': self.package_id,
            'category': self.category.value,
            'source_agent': self.source_agent,
            'title': self.title,
            'data': self.data,
            'schema_version': self.schema_version,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_public': self.is_public,
            'target_agents': self.target_agents,
            'tags': self.tags
        }


@dataclass
class TaskHandoff:
    """
    Standard format for transferring tasks between agents.
    """
    handoff_id: str
    from_agent: str
    to_agent: str
    task_type: str
    task_description: str
    context: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    deadline: Optional[datetime] = None
    callback_required: bool = False
    original_requester: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class CooperationProtocol:
    """
    The central cooperation protocol that all agents use.

    COOPERATION MANDATE:
    - Every agent MUST implement the handle_request method
    - Agents MUST respond to requests from other agents within their capability
    - Agents SHOULD proactively share useful data
    - Agents MUST NOT ignore or refuse valid requests from other agents
    """

    # Shared message bus for all agents
    _message_bus: queue.Queue = queue.Queue()
    _data_store: Dict[str, DataPackage] = {}
    _pending_responses: Dict[str, asyncio.Future] = {}
    _message_handlers: Dict[str, Callable] = {}
    _lock = threading.Lock()

    # Logger
    logger = logging.getLogger("agent.protocol")

    @classmethod
    def generate_id(cls, prefix: str = "msg") -> str:
        """Generate unique ID for messages/packages"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        rand = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        return f"{prefix}_{timestamp}_{rand}"

    @classmethod
    def send_message(cls, message: AgentMessage):
        """Send a message to another agent or broadcast"""
        cls._message_bus.put(message)
        cls.logger.debug(f"Message sent: {message.from_agent} -> {message.to_agent}: {message.subject}")

    @classmethod
    def receive_messages(cls, agent_id: str) -> List[AgentMessage]:
        """Receive all messages for a specific agent"""
        messages = []
        temp_queue = queue.Queue()

        with cls._lock:
            while not cls._message_bus.empty():
                try:
                    msg = cls._message_bus.get_nowait()
                    # Check if message is for this agent or is a broadcast
                    if msg.to_agent == agent_id or msg.to_agent == "*":
                        # Check TTL
                        age = (datetime.now() - msg.timestamp).total_seconds() / 60
                        if age <= msg.ttl_minutes:
                            messages.append(msg)
                    else:
                        temp_queue.put(msg)
                except queue.Empty:
                    break

            # Put back messages for other agents
            while not temp_queue.empty():
                cls._message_bus.put(temp_queue.get())

        return messages

    @classmethod
    async def request_help(
        cls,
        from_agent: str,
        to_agent: str,
        subject: str,
        request_data: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        timeout_seconds: int = 60
    ) -> Optional[AgentMessage]:
        """
        Send a request to another agent and wait for response.

        This is the primary method for inter-agent cooperation.
        All agents MUST respond to valid requests.
        """
        message_id = cls.generate_id("req")

        message = AgentMessage(
            message_id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.REQUEST,
            subject=subject,
            payload=request_data,
            priority=priority,
            requires_response=True
        )

        # Create a future for the response
        response_future = asyncio.Future()
        cls._pending_responses[message_id] = response_future

        # Send the request
        cls.send_message(message)

        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            return response
        except asyncio.TimeoutError:
            cls.logger.warning(f"Request timeout: {from_agent} -> {to_agent}: {subject}")
            return None
        finally:
            cls._pending_responses.pop(message_id, None)

    @classmethod
    def respond(cls, original_message: AgentMessage, response_data: Dict[str, Any]):
        """
        Respond to a request from another agent.

        MANDATORY: All agents must implement response logic.
        """
        response = AgentMessage(
            message_id=cls.generate_id("rsp"),
            from_agent=original_message.to_agent,
            to_agent=original_message.from_agent,
            message_type=MessageType.RESPONSE,
            subject=f"RE: {original_message.subject}",
            payload=response_data,
            response_to=original_message.message_id
        )

        cls.send_message(response)

        # Resolve pending future if exists
        if original_message.message_id in cls._pending_responses:
            future = cls._pending_responses[original_message.message_id]
            if not future.done():
                future.set_result(response)

    @classmethod
    def share_data(cls, package: DataPackage):
        """
        Share data with other agents.

        Agents SHOULD proactively share useful discoveries.
        """
        cls._data_store[package.package_id] = package

        # Notify interested agents
        if package.target_agents:
            for agent_id in package.target_agents:
                notification = AgentMessage(
                    message_id=cls.generate_id("ntf"),
                    from_agent=package.source_agent,
                    to_agent=agent_id,
                    message_type=MessageType.DATA_SHARE,
                    subject=f"New data available: {package.title}",
                    payload={'package_id': package.package_id, 'category': package.category.value}
                )
                cls.send_message(notification)

        cls.logger.info(f"Data shared: {package.source_agent} -> {package.title}")

    @classmethod
    def get_shared_data(
        cls,
        category: Optional[DataCategory] = None,
        tags: Optional[List[str]] = None,
        source_agent: Optional[str] = None
    ) -> List[DataPackage]:
        """
        Retrieve shared data from other agents.
        """
        results = []
        now = datetime.now()

        for package in cls._data_store.values():
            # Check expiration
            if package.expires_at and package.expires_at < now:
                continue

            # Apply filters
            if category and package.category != category:
                continue
            if source_agent and package.source_agent != source_agent:
                continue
            if tags and not any(t in package.tags for t in tags):
                continue

            if package.is_public:
                results.append(package)

        return results

    @classmethod
    def broadcast_alert(cls, from_agent: str, subject: str, alert_data: Dict[str, Any]):
        """
        Broadcast an urgent alert to all agents.
        """
        message = AgentMessage(
            message_id=cls.generate_id("alt"),
            from_agent=from_agent,
            to_agent="*",
            message_type=MessageType.ALERT,
            subject=subject,
            payload=alert_data,
            priority=Priority.URGENT
        )
        cls.send_message(message)
        cls.logger.warning(f"ALERT from {from_agent}: {subject}")

    @classmethod
    def handoff_task(cls, handoff: TaskHandoff):
        """
        Transfer a task to another agent.

        Used when one agent determines another is better suited for a task.
        """
        message = AgentMessage(
            message_id=cls.generate_id("hnd"),
            from_agent=handoff.from_agent,
            to_agent=handoff.to_agent,
            message_type=MessageType.HANDOFF,
            subject=f"Task Handoff: {handoff.task_type}",
            payload=handoff.to_dict(),
            priority=handoff.priority,
            requires_response=handoff.callback_required
        )
        cls.send_message(message)
        cls.logger.info(f"Task handoff: {handoff.from_agent} -> {handoff.to_agent}: {handoff.task_type}")


class CooperativeMixin:
    """
    Mixin class that adds cooperation capabilities to any agent.

    All specialized agents should inherit from this mixin to ensure
    they can participate in the cooperation protocol.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._message_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default message handlers"""
        self._message_handlers['status_request'] = self._handle_status_request
        self._message_handlers['capability_query'] = self._handle_capability_query
        self._message_handlers['data_request'] = self._handle_data_request

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type"""
        self._message_handlers[message_type] = handler

    async def process_messages(self):
        """Process incoming messages from other agents"""
        messages = CooperationProtocol.receive_messages(self.agent_id)

        for message in messages:
            await self._handle_message(message)

    async def _handle_message(self, message: AgentMessage):
        """
        Handle an incoming message.

        COOPERATION MANDATE: Agents MUST respond to valid requests.
        """
        self.logger.debug(f"Received: {message.from_agent} -> {message.subject}")

        # Handle based on message type
        if message.message_type == MessageType.REQUEST:
            handler = self._message_handlers.get(message.subject)
            if handler:
                try:
                    response_data = await handler(message.payload)
                    CooperationProtocol.respond(message, {
                        'success': True,
                        'data': response_data
                    })
                except Exception as e:
                    CooperationProtocol.respond(message, {
                        'success': False,
                        'error': str(e)
                    })
            else:
                # Default cooperative response
                CooperationProtocol.respond(message, {
                    'success': False,
                    'error': f"No handler for: {message.subject}",
                    'available_handlers': list(self._message_handlers.keys())
                })

        elif message.message_type == MessageType.HANDOFF:
            await self._handle_handoff(message)

        elif message.message_type == MessageType.ALERT:
            await self._handle_alert(message)

    async def _handle_status_request(self, payload: Dict) -> Dict:
        """Respond to status requests - all agents must support this"""
        return self.get_status_report()

    async def _handle_capability_query(self, payload: Dict) -> Dict:
        """Report agent capabilities"""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'handlers': list(self._message_handlers.keys()),
            'status': self.status.value
        }

    async def _handle_data_request(self, payload: Dict) -> Dict:
        """Handle requests for data from this agent"""
        # Override in subclasses to provide specific data
        return {'message': 'No specific data available'}

    async def _handle_handoff(self, message: AgentMessage):
        """Handle a task handoff from another agent"""
        # Override in subclasses for specific handoff logic
        self.logger.info(f"Received handoff from {message.from_agent}")

    async def _handle_alert(self, message: AgentMessage):
        """Handle an alert from another agent"""
        self.logger.warning(f"ALERT from {message.from_agent}: {message.subject}")

    async def request_from_agent(
        self,
        target_agent: str,
        subject: str,
        data: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Request help or data from another agent.

        Usage:
            result = await self.request_from_agent(
                'librarian',
                'get_breed_info',
                {'breed': 'Labrador Retriever'}
            )
        """
        response = await CooperationProtocol.request_help(
            from_agent=self.agent_id,
            to_agent=target_agent,
            subject=subject,
            request_data=data
        )

        if response and response.payload.get('success'):
            return response.payload.get('data')
        return None

    def share_discovery(
        self,
        category: DataCategory,
        title: str,
        data: Any,
        tags: Optional[List[str]] = None
    ):
        """
        Share a discovery with other agents.

        Usage:
            self.share_discovery(
                DataCategory.SHELTER,
                'New shelters found in NY',
                {'shelters': [...], 'count': 15},
                tags=['new', 'verified']
            )
        """
        package = DataPackage(
            package_id=CooperationProtocol.generate_id("pkg"),
            category=category,
            source_agent=self.agent_id,
            title=title,
            data=data,
            tags=tags or []
        )
        CooperationProtocol.share_data(package)

    def alert_all_agents(self, subject: str, alert_data: Dict[str, Any]):
        """Send an urgent alert to all agents"""
        CooperationProtocol.broadcast_alert(self.agent_id, subject, alert_data)

    def handoff_to_agent(
        self,
        to_agent: str,
        task_type: str,
        description: str,
        context: Dict[str, Any],
        priority: Priority = Priority.NORMAL
    ):
        """
        Hand off a task to another agent better suited for it.

        Usage:
            self.handoff_to_agent(
                'content_writer',
                'write_bio',
                'Write adoption bio for animal',
                {'animal_id': 123, 'details': {...}}
            )
        """
        handoff = TaskHandoff(
            handoff_id=CooperationProtocol.generate_id("hnd"),
            from_agent=self.agent_id,
            to_agent=to_agent,
            task_type=task_type,
            task_description=description,
            context=context,
            priority=priority
        )
        CooperationProtocol.handoff_task(handoff)
