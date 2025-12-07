#!/usr/bin/env python3
"""
===============================================================================
Translation Agent - Multi-language Support
===============================================================================
Handles translation of content to multiple languages.

Cooperates with: ContentWriter, Marketing, SEO
===============================================================================
"""

import os, sys, asyncio
from datetime import datetime
from typing import Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory


class TranslationAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(self, agent_id="translation", agent_name="Translation Agent",
                          agent_type="specialized_agent", description="Multi-language translation")
        CooperativeMixin.__init__(self)
        self.supported_languages = ['en', 'es', 'fr', 'de', 'pt', 'zh', 'ja', 'ko']
        self.register_handler('translate', self._handle_translate)
        self.register_handler('get_languages', self._handle_languages)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        if task.task_type == "translate":
            result = await self.translate(task.payload)
        else:
            result = {'error': f"Unknown task: {task.task_type}"}
        return AgentResult(success=True, message="Translation task completed", data=result)

    async def run(self) -> AgentResult:
        self.logger.info("Translation Agent starting")
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task: await self.execute_task(task)
            else: await asyncio.sleep(1)
        return AgentResult(success=True, message="Translation Agent completed")

    async def translate(self, params: Dict) -> Dict:
        text = params.get('text', '')
        target_lang = params.get('target', 'es')
        source_lang = params.get('source', 'en')

        # In production, would use translation API
        translations = {
            'es': {'adopt': 'adoptar', 'dog': 'perro', 'cat': 'gato', 'shelter': 'refugio'},
            'fr': {'adopt': 'adopter', 'dog': 'chien', 'cat': 'chat', 'shelter': 'refuge'}
        }

        translated = text
        if target_lang in translations:
            for eng, trans in translations[target_lang].items():
                translated = translated.replace(eng, trans)

        return {'original': text, 'translated': translated, 'source': source_lang, 'target': target_lang}

    async def _handle_translate(self, payload: Dict) -> Dict:
        return await self.translate(payload)
    async def _handle_languages(self, payload: Dict) -> Dict:
        return {'languages': self.supported_languages}
