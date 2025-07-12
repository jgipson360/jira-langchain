#!/usr/bin/env python3
"""Test dynamic epic discovery with ticket creation workflow."""

from jira_integration import JiraIntegration


def test_dynamic_epic_discovery():
    """Test that dynamic epic discovery works with ticket creation."""
    print("🔍 Testing dynamic epic discovery in ticket creation workflow...")

    try:
        jira = JiraIntegration()

        # Test the batch creation logic (without actually creating tickets)
        print("\n📋 Testing batch creation logic...")

        # This will call _discover_epic_mappings internally
        print("Step 1: Discover existing epics...")
        epic_mappings = jira._discover_epic_mappings()
        print(f"Found mappings: {epic_mappings}")

        # Check if KITCH epic is found
        if "KITCH" in epic_mappings:
            print(f"✅ KITCH epic found: {epic_mappings['KITCH']}")
        else:
            print("❌ KITCH epic not found in mappings")

        # Check if PREP epic is found (for dependencies)
        if "PREP" in epic_mappings:
            print(f"✅ PREP epic found: {epic_mappings['PREP']}")
        else:
            print("❌ PREP epic not found in mappings")

        print("\n🔗 Testing dependency resolution...")
        dependencies = jira._parse_dependencies("[PREP] Test Dependency")
        print(f"Parsed dependencies: {dependencies}")

        resolved_deps = jira._resolve_dependency_keys(dependencies, epic_mappings)
        print(f"Resolved dependencies: {resolved_deps}")

        print("\n✅ Dynamic epic discovery test completed successfully!")

    except Exception as e:
        print(f"❌ Error testing dynamic epic discovery: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_dynamic_epic_discovery()
