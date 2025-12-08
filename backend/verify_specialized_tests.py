#!/usr/bin/env python3
"""
Verification script for specialized agents tests
Simply verifies that tests can be imported and basic structure is correct
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

print("="*70)
print("SPECIALIZED AGENTS TEST VERIFICATION")
print("="*70)

print("\n1. Testing imports...")
try:
    from tests.test_specialized_agents import (
        TestMarketingAgent,
        TestSocialMediaAgent,
        TestEmailCampaignAgent,
        TestVideoGeneratorAgent,
        TestSEOAgent,
        TestDataQualityAgent,
        TestAdoptionMatcherAgent,
        TestStateAgent,
        TestAgentCooperation
    )
    print("   SUCCESS: All test classes imported")
except Exception as e:
    print(f"   FAIL: Import error - {e}")
    sys.exit(1)

print("\n2. Verifying test class structure...")
test_classes = {
    'MarketingAgent': TestMarketingAgent,
    'SocialMediaAgent': TestSocialMediaAgent,
    'EmailCampaignAgent': TestEmailCampaignAgent,
    'VideoGeneratorAgent': TestVideoGeneratorAgent,
    'SEOAgent': TestSEOAgent,
    'DataQualityAgent': TestDataQualityAgent,
    'AdoptionMatcherAgent': TestAdoptionMatcherAgent,
    'StateAgent': TestStateAgent,
    'AgentCooperation': TestAgentCooperation
}

total_tests = 0
for name, test_class in test_classes.items():
    test_methods = [m for m in dir(test_class) if m.startswith('test_')]
    print(f"   {name}: {len(test_methods)} tests")
    total_tests += len(test_methods)

print(f"\n   Total test methods: {total_tests}")

print("\n3. Verifying test coverage for each agent...")
coverage_requirements = {
    'MarketingAgent': ['initialization', 'create_campaign', 'execute_task', 'error_handling'],
    'SocialMediaAgent': ['initialization', 'generate_instagram_post', 'generate_tweet', 'generate_tiktok_script'],
    'EmailCampaignAgent': ['initialization', 'create_campaign', 'send_newsletter', 'error_handling'],
    'VideoGeneratorAgent': ['initialization', 'create_video', 'create_slideshow', 'error_handling'],
    'SEOAgent': ['initialization', 'keyword_research', 'analyze_content', 'generate_meta', 'error_handling'],
    'DataQualityAgent': ['initialization', 'run_audit', 'find_duplicates', 'cleanup', 'normalize_data', 'error_handling'],
    'AdoptionMatcherAgent': ['initialization', 'find_matches', 'calculate_match_score', 'error_handling'],
    'StateAgent': ['initialization', 'is_valid_shelter', 'normalize_shelter_name', 'verify_shelter', 'error_handling']
}

all_covered = True
for agent_name, required in coverage_requirements.items():
    test_class = test_classes[agent_name]
    test_methods = [m.replace('test_', '').replace(agent_name.lower() + '_', '')
                   for m in dir(test_class) if m.startswith('test_')]

    missing = []
    for req in required:
        if not any(req in method for method in test_methods):
            missing.append(req)

    if missing:
        print(f"   WARNING: {agent_name} missing tests: {missing}")
        all_covered = False
    else:
        print(f"   OK: {agent_name} - all requirements covered")

if all_covered:
    print("\n   All coverage requirements met!")
else:
    print("\n   Some coverage gaps found (see warnings above)")

print("\n4. Testing agent instantiation with mocks...")
from unittest.mock import patch, MagicMock

try:
    with patch('agents.base_agent.init_db'):
        with patch('agents.base_agent.SessionLocal'):
            # Test MarketingAgent
            from agents.specialized.marketing_agent import MarketingAgent
            ma = MarketingAgent()
            assert ma.agent_id == "marketing"
            print("   OK: MarketingAgent instantiated")

            # Test EmailCampaignAgent
            from agents.specialized.email_agent import EmailCampaignAgent
            ea = EmailCampaignAgent()
            assert ea.agent_id == "email_campaign"
            print("   OK: EmailCampaignAgent instantiated")

            # Test VideoGeneratorAgent
            with patch('agents.specialized.video_agent.settings') as mock_settings:
                mock_settings.VIDEO_OUTPUT_DIR = '/tmp/videos'
                from agents.specialized.video_agent import VideoGeneratorAgent
                va = VideoGeneratorAgent()
                assert va.agent_id == "video_generator"
                print("   OK: VideoGeneratorAgent instantiated")

            # Test SEOAgent
            from agents.specialized.seo_agent import SEOAgent
            sa = SEOAgent()
            assert sa.agent_id == "seo"
            print("   OK: SEOAgent instantiated")

            # Test DataQualityAgent
            from agents.specialized.data_quality_agent import DataQualityAgent
            dqa = DataQualityAgent()
            assert dqa.agent_id == "data_quality"
            print("   OK: DataQualityAgent instantiated")

            # Test AdoptionMatcherAgent
            from agents.specialized.matcher_agent import AdoptionMatcherAgent
            ama = AdoptionMatcherAgent()
            assert ama.agent_id == "adoption_matcher"
            print("   OK: AdoptionMatcherAgent instantiated")

            # Test StateAgent
            from agents.state_agents.state_agent import StateAgent
            sta = StateAgent('CA')
            assert sta.state_code == "CA"
            print("   OK: StateAgent instantiated")

    # Test SocialMediaAgent (no BaseAgent inheritance)
    from agents.social_agent import SocialMediaAgent
    sma = SocialMediaAgent()
    print("   OK: SocialMediaAgent instantiated")

    print("\n   All agents instantiated successfully!")

except Exception as e:
    print(f"   FAIL: Instantiation error - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. Verifying async test methods...")
import asyncio
import inspect

async_test_count = 0
for name, test_class in test_classes.items():
    for method_name in dir(test_class):
        if method_name.startswith('test_'):
            method = getattr(test_class, method_name)
            if asyncio.iscoroutinefunction(method):
                async_test_count += 1

print(f"   Found {async_test_count} async test methods")

print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70)
print(f"\nSummary:")
print(f"  - 9 test classes defined")
print(f"  - {total_tests} total test methods")
print(f"  - {async_test_count} async test methods")
print(f"  - All agents can be instantiated")
print(f"  - Test coverage: {'COMPLETE' if all_covered else 'PARTIAL'}")
print("\nTo run tests with pytest (when conftest issues are resolved):")
print("  pytest backend/tests/test_specialized_agents.py -v")
print("="*70)
