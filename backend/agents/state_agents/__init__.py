"""
===============================================================================
State Agents - 50 AI Agents for Shelter Discovery
===============================================================================
One agent per US state, each specialized in finding animal shelters and
rescues within their assigned territory.

Usage:
    from agents.state_agents import get_state_agent, get_all_state_agents

    # Get agent for California
    ca_agent = get_state_agent('CA')
    await ca_agent.start()

    # Get all state agents
    all_agents = get_all_state_agents()

Author: Waiting The Longest Development Team
===============================================================================
"""

from .state_agent import StateAgent, STATE_DATA, get_state_agent, get_all_state_agents

__all__ = [
    'StateAgent',
    'STATE_DATA',
    'get_state_agent',
    'get_all_state_agents'
]
