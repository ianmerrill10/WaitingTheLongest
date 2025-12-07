# Waiting The Longest - Agent Army Documentation

## Overview

This document describes the comprehensive AI agent system powering Waiting The Longest. The system consists of **82 specialized agents** working together to discover shelters, manage content, process data, and promote animal adoption.

## Table of Contents

1. [Architecture](#architecture)
2. [Agent-to-Agent Protocol](#agent-to-agent-protocol)
3. [State Agents (50)](#state-agents)
4. [Orchestrator](#orchestrator)
5. [Specialized Agents (32)](#specialized-agents)
6. [CLI Commands](#cli-commands)
7. [Integration Guide](#integration-guide)

---

## Architecture

```
                    ┌─────────────────────┐
                    │   ORCHESTRATOR      │
                    │  (Central Command)  │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌─────▼─────┐          ┌────▼────┐
   │  STATE  │           │SPECIALIZED│          │PROTOCOLS│
   │ AGENTS  │◄─────────►│  AGENTS   │◄────────►│ (Comms) │
   │  (50)   │           │   (32)    │          │         │
   └─────────┘           └───────────┘          └─────────┘
```

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `base_agent.py` | `backend/agents/` | Abstract base class for all agents |
| `protocols.py` | `backend/agents/` | Agent-to-agent communication protocol |
| `orchestrator.py` | `backend/agents/` | Central command and coordination |
| `state_agents/` | `backend/agents/` | 50 state-specific discovery agents |
| `specialized/` | `backend/agents/` | 32 specialized task agents |

---

## Agent-to-Agent Protocol

**CORE PRINCIPLE: All agents MUST cooperate and help each other when requested.**

### Communication Types

| Type | Purpose | Example |
|------|---------|---------|
| `REQUEST` | Ask for help/data | "Get breed info for Labrador" |
| `RESPONSE` | Reply to request | Breed data returned |
| `BROADCAST` | Message to all agents | "System alert" |
| `DATA_SHARE` | Share discoveries | "New shelters found in NY" |
| `HANDOFF` | Transfer task | "Content Writer, write this bio" |
| `ALERT` | Urgent notification | "API down" |

### Making Requests

```python
# Any agent can request help from another
result = await self.request_from_agent(
    'librarian',           # Target agent
    'get_breed_info',      # Handler name
    {'breed': 'Labrador'}  # Payload
)
```

### Sharing Data

```python
# Share discoveries with interested agents
self.share_discovery(
    DataCategory.SHELTER,
    'New shelters found in NY',
    {'shelters': [...], 'count': 15},
    tags=['new', 'verified', 'NY']
)
```

### Handing Off Tasks

```python
# Transfer task to more appropriate agent
self.handoff_to_agent(
    'content_writer',      # Target agent
    'write_bio',           # Task type
    'Write adoption bio',  # Description
    {'animal_id': 123}     # Context
)
```

---

## State Agents

**50 agents, one for each US state**, responsible for discovering shelters and rescues.

### Usage

```bash
# Run single state
python -m agents.state_agents.state_agent --state NY

# Run all states
python -m agents.state_agents.state_agent --all

# Run by region
python -m agents.state_agents.state_agent --region Northeast
```

### Regions

| Region | States |
|--------|--------|
| Northeast | CT, DE, MA, MD, ME, NH, NJ, NY, PA, RI, VT |
| Southeast | AL, AR, FL, GA, KY, LA, MS, NC, SC, TN, VA, WV |
| Midwest | IA, IL, IN, KS, MI, MN, MO, ND, NE, OH, SD, WI |
| Southwest | AZ, NM, OK, TX |
| West | AK, CA, CO, HI, ID, MT, NV, OR, UT, WA, WY |

### State Agent Methods

| Method | Description |
|--------|-------------|
| `search_rescuegroups()` | Search RescueGroups API |
| `search_directory_sites()` | Scrape shelter directories |
| `search_cities()` | Search by major cities |
| `verify_shelter()` | Verify shelter data |
| `save_shelter_to_db()` | Save to database |

---

## Orchestrator

The central command that coordinates all agents.

### Usage

```bash
# Show status
python -m agents.orchestrator --status

# List all agents
python -m agents.orchestrator --list-agents

# Run discovery for specific states
python -m agents.orchestrator --discovery NY CA TX

# Run discovery for region
python -m agents.orchestrator --region Northeast

# Run social media campaign
python -m agents.orchestrator --social

# Run maintenance cycle
python -m agents.orchestrator --maintenance

# Start specific agent
python -m agents.orchestrator --start marketing

# Stop agent
python -m agents.orchestrator --stop marketing
```

### Orchestrator Methods

| Method | Description |
|--------|-------------|
| `run_state_discovery(states, region)` | Run shelter discovery |
| `run_social_media_campaign()` | Coordinate social posts |
| `run_maintenance_cycle()` | Run cleanup tasks |
| `start_agent(agent_id)` | Start specific agent |
| `stop_agent(agent_id)` | Stop running agent |
| `get_status_report()` | Get system status |

---

## Specialized Agents

### Social Media Group

#### Marketing Agent (`marketing`)
Strategic marketing campaign manager.

```bash
python -m agents.specialized.marketing_agent --create-campaign "Holiday Adoption"
python -m agents.specialized.marketing_agent --suggest "senior dogs"
python -m agents.specialized.marketing_agent --daily
```

| Handler | Description |
|---------|-------------|
| `get_active_campaigns` | Get running campaigns |
| `content_suggestion` | Get content ideas |
| `schedule_content` | Schedule posts |

#### TikTok Agent (`tiktok`)
TikTok content creation and posting.

```bash
python -m agents.specialized.tiktok_agent --create
python -m agents.specialized.tiktok_agent --trends
python -m agents.specialized.tiktok_agent --caption "Buddy"
```

| Handler | Description |
|---------|-------------|
| `create_content` | Create TikTok video |
| `start_campaign` | Start campaign |
| `get_performance` | Get metrics |
| `get_trends` | Get trending topics |

#### Instagram Agent (`instagram`)
Instagram content management.

```bash
python -m agents.specialized.instagram_agent --post
python -m agents.specialized.instagram_agent --reel
python -m agents.specialized.instagram_agent --hashtags dog
```

| Handler | Description |
|---------|-------------|
| `create_content` | Create post/reel |
| `start_campaign` | Start campaign |
| `get_performance` | Get metrics |
| `post_animal` | Post animal content |

#### Facebook Agent (`facebook`)
Facebook posts, events, and fundraisers.

```bash
python -m agents.specialized.facebook_agent --post
python -m agents.specialized.facebook_agent --event "Adoption Day"
python -m agents.specialized.facebook_agent --fundraiser "Help Our Shelter"
```

| Handler | Description |
|---------|-------------|
| `create_content` | Create post |
| `create_event` | Create event |
| `create_fundraiser` | Start fundraiser |
| `get_performance` | Get metrics |

---

### Data Processing Group

#### Librarian Agent (`librarian`)
Central knowledge and data hub. **All agents can query the Librarian.**

```bash
python -m agents.specialized.librarian_agent --stats
python -m agents.specialized.librarian_agent --longest 10
python -m agents.specialized.librarian_agent --search "labrador"
python -m agents.specialized.librarian_agent --animal 123
python -m agents.specialized.librarian_agent --breed "Golden Retriever"
```

| Handler | Description |
|---------|-------------|
| `get_animal` | Get animal profile |
| `get_breed_info` | Get breed information |
| `get_shelter` | Get shelter info |
| `search` | Search knowledge base |
| `get_longest_waiting` | Get longest waiting animals |
| `add_knowledge` | Add knowledge entry |

#### Data Quality Agent (`data_quality`)
Validates and cleans data.

```bash
python -m agents.specialized.data_quality_agent --audit all
python -m agents.specialized.data_quality_agent --duplicates shelters
python -m agents.specialized.data_quality_agent --cleanup orphans
```

| Handler | Description |
|---------|-------------|
| `run_audit` | Run data audit |
| `find_duplicates` | Find duplicates |
| `cleanup` | Run cleanup |
| `get_quality_score` | Get quality score |

#### Intake Specialist Agent (`intake_specialist`)
Processes new animal intakes.

| Handler | Description |
|---------|-------------|
| `process_intake` | Process new animal |
| `validate` | Validate data |
| `enrich` | Enrich profile |
| `get_pending` | Get pending intakes |

#### Image Processing Agent (`image_processing`)
Optimizes and processes images.

| Handler | Description |
|---------|-------------|
| `process_animal_photo` | Process photo |
| `optimize_for_instagram` | Optimize for IG |
| `get_animal_image` | Get animal image |
| `create_thumbnail` | Create thumbnail |

#### Translation Agent (`translation`)
Multi-language support.

| Handler | Description |
|---------|-------------|
| `translate` | Translate text |
| `get_languages` | Get supported languages |

---

### Operations Group

#### Debugging Agent (`debugging`)
System diagnostics and health monitoring.

```bash
python -m agents.specialized.debugging_agent --health
python -m agents.specialized.debugging_agent --logs
python -m agents.specialized.debugging_agent --resources
python -m agents.specialized.debugging_agent --diagnose "connection timeout"
```

| Handler | Description |
|---------|-------------|
| `health_check` | Run health check |
| `diagnose_error` | Diagnose error |
| `report_error` | Report error |
| `get_status` | Get debug status |

#### Accounting Agent (`accounting`)
Financial tracking.

```bash
python -m agents.specialized.accounting_agent --balance
python -m agents.specialized.accounting_agent --report month
```

| Handler | Description |
|---------|-------------|
| `record_donation` | Record donation |
| `record_expense` | Record expense |
| `get_summary` | Get financial summary |
| `get_balance` | Get current balance |

#### Scheduler Agent (`scheduler`)
Task scheduling and automation.

| Handler | Description |
|---------|-------------|
| `schedule_job` | Schedule a job |
| `get_schedule` | Get schedule |
| `cancel_job` | Cancel job |

#### Backup Agent (`backup`)
Data backup and recovery.

| Handler | Description |
|---------|-------------|
| `create_backup` | Create backup |
| `restore` | Restore backup |
| `list_backups` | List backups |

#### Compliance Agent (`compliance`)
Regulatory compliance.

| Handler | Description |
|---------|-------------|
| `run_audit` | Run compliance audit |
| `check_policy` | Check policy |

---

### Marketing Group

#### SEO Agent (`seo`)
Search engine optimization.

| Handler | Description |
|---------|-------------|
| `get_keywords` | Get keyword suggestions |
| `analyze_content` | Analyze content SEO |
| `generate_meta` | Generate meta tags |

#### Email Campaign Agent (`email_campaign`)
Email marketing.

| Handler | Description |
|---------|-------------|
| `create_campaign` | Create email campaign |
| `send_newsletter` | Send newsletter |
| `get_stats` | Get email stats |

#### Content Writer Agent (`content_writer`)
Content creation.

| Handler | Description |
|---------|-------------|
| `write_bio` | Write animal bio |
| `write_social_post` | Write social post |
| `write_newsletter` | Write newsletter |
| `prepare_campaign_content` | Prepare campaign |

#### Video Generator Agent (`video_generator`)
Video content creation.

| Handler | Description |
|---------|-------------|
| `create_short_video` | Create short video |
| `create_slideshow` | Create slideshow |
| `add_music` | Add music to video |

---

### Monitoring Group

#### Alert Monitor Agent (`alert_monitor`)
System alerts and notifications.

| Handler | Description |
|---------|-------------|
| `create_alert` | Create alert |
| `get_alerts` | Get alerts |
| `acknowledge` | Acknowledge alert |

#### API Monitor Agent (`api_monitor`)
External API monitoring.

| Handler | Description |
|---------|-------------|
| `check_api` | Check specific API |
| `get_status` | Get API statuses |
| `check_all` | Check all APIs |

#### Analytics Agent (`analytics`)
Data analytics and insights.

| Handler | Description |
|---------|-------------|
| `get_adoption_stats` | Get adoption statistics |
| `get_campaign_metrics` | Get campaign metrics |
| `get_trends` | Get trends |
| `get_dashboard` | Get dashboard data |

#### Sentiment Analysis Agent (`sentiment_analysis`)
Social sentiment monitoring.

| Handler | Description |
|---------|-------------|
| `analyze_text` | Analyze sentiment |
| `get_trends` | Get sentiment trends |

#### Competitor Watch Agent (`competitor_watch`)
Competitive intelligence.

| Handler | Description |
|---------|-------------|
| `get_insights` | Get competitor insights |
| `analyze_competitor` | Analyze competitor |

---

### Support Group

#### Donation Tracker Agent (`donation_tracker`)
Donation management.

| Handler | Description |
|---------|-------------|
| `record_donation` | Record donation |
| `track_fundraiser` | Track fundraiser |
| `get_total` | Get donation total |

#### Volunteer Coordinator Agent (`volunteer_coordinator`)
Volunteer management.

| Handler | Description |
|---------|-------------|
| `register_volunteer` | Register volunteer |
| `schedule_shift` | Schedule shift |
| `get_schedule` | Get schedule |

#### Adoption Matcher Agent (`adoption_matcher`)
Pet-adopter matching.

| Handler | Description |
|---------|-------------|
| `find_matches` | Find matching pets |
| `score_match` | Score a match |

#### Notification Agent (`notification`)
User notifications.

| Handler | Description |
|---------|-------------|
| `send_notification` | Send notification |
| `send_push` | Send push notification |
| `send_sms` | Send SMS |

#### Report Generator Agent (`report_generator`)
Report creation.

| Handler | Description |
|---------|-------------|
| `generate_report` | Generate report |
| `get_reports` | List reports |

#### Chat Support Agent (`chat_support`)
User chat support.

| Handler | Description |
|---------|-------------|
| `handle_message` | Handle chat message |
| `get_faq` | Get FAQ |

---

## CLI Commands

### Quick Reference

```bash
# Orchestrator
python -m agents.orchestrator --status
python -m agents.orchestrator --list-agents
python -m agents.orchestrator --discovery NY CA
python -m agents.orchestrator --social
python -m agents.orchestrator --maintenance

# State Agents
python -m agents.state_agents.state_agent --state CA
python -m agents.state_agents.state_agent --all
python -m agents.state_agents.state_agent --region West

# Individual Agents (examples)
python -m agents.specialized.debugging_agent --health
python -m agents.specialized.librarian_agent --stats
python -m agents.specialized.marketing_agent --daily
python -m agents.specialized.data_quality_agent --audit all
```

---

## Integration Guide

### Creating a New Agent

1. Create file in `backend/agents/specialized/`
2. Inherit from `BaseAgent` and `CooperativeMixin`
3. Register handlers in `__init__`
4. Implement `execute_task()` and `run()`
5. Add to `specialized/__init__.py`
6. Register in `orchestrator.py`

### Example Agent Template

```python
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from agents.protocols import CooperativeMixin, DataCategory

class MyNewAgent(CooperativeMixin, BaseAgent):
    def __init__(self):
        BaseAgent.__init__(
            self,
            agent_id="my_agent",
            agent_name="My New Agent",
            agent_type="specialized_agent",
            description="What this agent does"
        )
        CooperativeMixin.__init__(self)

        # Register handlers for other agents to call
        self.register_handler('my_handler', self._handle_my_request)

    async def execute_task(self, task: AgentTask) -> AgentResult:
        # Handle task execution
        pass

    async def run(self) -> AgentResult:
        # Main agent loop
        while self.status.value == "running":
            await self.process_messages()
            task = self.get_next_task()
            if task:
                await self.execute_task(task)
            await asyncio.sleep(1)
        return AgentResult(success=True, message="Complete")

    async def _handle_my_request(self, payload: Dict) -> Dict:
        # Handle requests from other agents
        return {'result': 'data'}
```

---

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| State Agents | 50 | One per US state for shelter discovery |
| Specialized Agents | 32 | Task-specific agents |
| Orchestrator | 1 | Central command |
| **Total** | **83** | Complete agent army |

**Remember: All agents are cooperative. When asked for help, agents MUST respond helpfully.**

---

*Generated for Waiting The Longest - Because Every Day Matters*
