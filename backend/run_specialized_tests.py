#!/usr/bin/env python3
"""
Simple test runner for specialized agents tests
Bypasses conftest.py to avoid import errors
"""

import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Import test classes
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

def run_sync_tests(test_class, class_name):
    """Run synchronous tests from a test class"""
    print(f"\n{'='*70}")
    print(f"Running {class_name} Tests")
    print('='*70)

    test_instance = test_class()
    if hasattr(test_instance, 'setup'):
        test_instance.setup()

    passed = 0
    failed = 0

    for attr_name in dir(test_instance):
        if attr_name.startswith('test_') and not attr_name.endswith('asyncio'):
            try:
                method = getattr(test_instance, attr_name)
                if callable(method):
                    # Check if it needs a fixture
                    import inspect
                    sig = inspect.signature(method)
                    params = list(sig.parameters.keys())

                    if len(params) > 0:
                        # Call fixture method
                        fixture_name = params[0]
                        if hasattr(test_instance, fixture_name):
                            fixture = getattr(test_instance, fixture_name)()
                            method(fixture)
                        else:
                            print(f"  SKIP: {attr_name} (needs fixture {fixture_name})")
                            continue
                    else:
                        method()

                    print(f"  PASS: {attr_name}")
                    passed += 1
            except Exception as e:
                print(f"  FAIL: {attr_name}")
                print(f"    Error: {str(e)[:100]}")
                failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed

def run_async_tests(test_class, class_name):
    """Run async tests from a test class"""
    print(f"\n{'='*70}")
    print(f"Running {class_name} Async Tests")
    print('='*70)

    test_instance = test_class()
    if hasattr(test_instance, 'setup'):
        test_instance.setup()

    passed = 0
    failed = 0

    for attr_name in dir(test_instance):
        if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(test_instance, attr_name)):
            try:
                method = getattr(test_instance, attr_name)

                # Check if it needs a fixture
                import inspect
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())

                if len(params) > 0:
                    # Call fixture method
                    fixture_name = params[0]
                    if hasattr(test_instance, fixture_name):
                        fixture_method = getattr(test_instance, fixture_name)
                        fixture = fixture_method()
                        asyncio.run(method(fixture))
                    else:
                        print(f"  SKIP: {attr_name} (needs fixture {fixture_name})")
                        continue
                else:
                    asyncio.run(method())

                print(f"  PASS: {attr_name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {attr_name}")
                print(f"    Error: {str(e)[:100]}")
                failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SPECIALIZED AGENTS TEST SUITE")
    print("="*70)

    total_passed = 0
    total_failed = 0

    test_classes = [
        (TestMarketingAgent, "MarketingAgent"),
        (TestSocialMediaAgent, "SocialMediaAgent"),
        (TestEmailCampaignAgent, "EmailCampaignAgent"),
        (TestVideoGeneratorAgent, "VideoGeneratorAgent"),
        (TestSEOAgent, "SEOAgent"),
        (TestDataQualityAgent, "DataQualityAgent"),
        (TestAdoptionMatcherAgent, "AdoptionMatcherAgent"),
        (TestStateAgent, "StateAgent"),
        (TestAgentCooperation, "AgentCooperation")
    ]

    for test_class, name in test_classes:
        # Run sync tests
        p1, f1 = run_sync_tests(test_class, name)
        total_passed += p1
        total_failed += f1

        # Run async tests
        p2, f2 = run_async_tests(test_class, name)
        total_passed += p2
        total_failed += f2

    print("\n" + "="*70)
    print(f"OVERALL RESULTS: {total_passed} passed, {total_failed} failed")
    print("="*70 + "\n")

    sys.exit(0 if total_failed == 0 else 1)
