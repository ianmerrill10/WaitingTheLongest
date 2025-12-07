#!/usr/bin/env python3
"""
===============================================================================
Chat Support Agent - User Chat Support
===============================================================================
Handles user chat support and FAQ responses.

Cooperates with: Librarian, Notification, AdoptionMatcher
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class ChatSupportAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="chat_support", agent_name="Chat Support Agent",
                          agent_type="specialized_agent", description="User chat support")
        CooperativeMixin.__init__(self)
        self.conversations: Dict[str, List[Dict]] = {}
        self.faq = {
            'adoption': 'To adopt, visit our website and fill out an application!',
            'hours': 'Shelter hours vary by location. Check the shelter page for details.',
            'fees': 'Adoption fees typically range from $50-$300 depending on the animal.',
            'process': 'The adoption process includes application, meet & greet, and home check.'
        }
        self.register_handler('handle_message', self._handle_message)
        self.register_handler('get_faq', self._handle_faq)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "handle_message":
            result = await self.handle_message(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Chat task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Chat Support Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Chat Agent completed")

    async def handle_message(self, params: Dict) -> Dict:
        user_id = params.get('user_id', 'anonymous')
        message = params.get('message', '').lower()

        # Check FAQ keywords
        response = None
        for keyword, answer in self.faq.items():
            if keyword in message:
                response = answer
                break

        if not response:
            if 'find' in message or 'looking for' in message:
                response = "I can help you find a pet! What type of animal are you looking for?"
            elif 'help' in message:
                response = "I'm here to help! You can ask about adoption, shelter hours, fees, or the adoption process."
            else:
                response = "Thanks for your message! How can I help you today? Ask about adoption, fees, or finding a pet."

        # Store conversation
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        self.conversations[user_id].append({'user': message, 'bot': response, 'time': datetime.now().isoformat()})

        return {'response': response, 'user_id': user_id}

    async def _handle_message(self, payload: Dict) -> Dict:
        return await self.handle_message(payload)
    async def _handle_faq(self, payload: Dict) -> Dict:
        return {'faq': self.faq}
