#!/usr/bin/env python3
"""
Verification script for Scout feature.

Tests:
1. GET /api/scout/feeds → triggers lazy seed (3 defaults disabled)
2. POST create temp feed (enabled) with url="fixture://local"
3. POST /api/scout/fetch?mode=fixture
4. GET /api/scout/items?hours=24 → verify >=2 items
5. POST fetch again → verify item count does not increase (dedup)
6. DELETE temp feed (disable)
"""
import sys
import os
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

API_BASE = os.getenv("API_URL", "http://localhost:8000")
AUTH = (os.getenv("AUTH_USER", "admin"), os.getenv("AUTH_PASS", "password"))

os.environ["DEBUG"] = "true"

def main():
    print("=" * 70)
    print("SCOUT VERIFICATION")
    print("=" * 70)
    print()
    
    passed = 0
    total = 0
    
    # Test 1: GET /api/scout/feeds → triggers lazy seed
    total += 1
    print("1. GET /api/scout/feeds (should trigger lazy seed)...")
    try:
        response = requests.get(
            f"{API_BASE}/api/scout/feeds",
            auth=AUTH
        )
        response.raise_for_status()
        feeds = response.json()
        
        if len(feeds) < 3:
            print(f"✗ FAILED: Expected at least 3 feeds (defaults), got {len(feeds)}")
        else:
            # Check that defaults exist
            default_names = {"Göteborgs tingsrätt", "Polisen Göteborg", "TT"}
            found_names = {f["name"] for f in feeds}
            if not default_names.issubset(found_names):
                print(f"✗ FAILED: Missing default feeds. Found: {found_names}")
            else:
                # Check that defaults are disabled
                defaults = [f for f in feeds if f["name"] in default_names]
                all_disabled = all(not f["is_enabled"] for f in defaults)
                if not all_disabled:
                    print(f"✗ FAILED: Some default feeds are enabled")
                else:
                    print(f"✓ PASSED: Lazy seed created 3 default feeds (disabled)")
                    passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
    print()
    
    # Test 2: POST create temp feed
    total += 1
    print("2. POST create temp feed (enabled)...")
    try:
        response = requests.post(
            f"{API_BASE}/api/scout/feeds",
            json={"name": "Test Feed", "url": "fixture://local"},
            auth=AUTH
        )
        response.raise_for_status()
        temp_feed = response.json()
        temp_feed_id = temp_feed["id"]
        
        if not temp_feed["is_enabled"]:
            print(f"✗ FAILED: Feed should be enabled")
        elif temp_feed["name"] != "Test Feed":
            print(f"✗ FAILED: Name mismatch")
        else:
            print(f"✓ PASSED: Temp feed created (ID: {temp_feed_id})")
            passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        temp_feed_id = None
    print()
    
    if not temp_feed_id:
        print("⚠ Skipping remaining tests (temp feed creation failed)")
        print("=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"Passed: {passed}/{total}")
        print()
        if passed == total:
            print("✅ ALL TESTS PASSED")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1
    
    # Test 3: POST /api/scout/fetch?mode=fixture
    total += 1
    print("3. POST /api/scout/fetch?mode=fixture...")
    try:
        # Verify feed is enabled before fetch
        response_check = requests.get(
            f"{API_BASE}/api/scout/feeds",
            auth=AUTH
        )
        response_check.raise_for_status()
        feeds_check = response_check.json()
        feed_check = next((f for f in feeds_check if f["id"] == temp_feed_id), None)
        if not feed_check or not feed_check["is_enabled"]:
            print(f"✗ FAILED: Temp feed not enabled before fetch")
        else:
            response = requests.post(
                f"{API_BASE}/api/scout/fetch?mode=fixture",
                auth=AUTH
            )
            response.raise_for_status()
            result = response.json()
            
            # Results keys are strings, convert temp_feed_id to string
            results = result.get("results", {})
            item_count = results.get(str(temp_feed_id), results.get(temp_feed_id, 0))
            
            if str(temp_feed_id) not in results and temp_feed_id not in results:
                print(f"✗ FAILED: Temp feed not in results. Results: {results}")
            else:
                if item_count < 2:
                    print(f"✗ FAILED: Expected at least 2 items, got {item_count}")
                else:
                    print(f"✓ PASSED: Fetch created {item_count} items")
                    passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 4: GET /api/scout/items?hours=24
    total += 1
    print("4. GET /api/scout/items?hours=24...")
    initial_count = 0
    try:
        response = requests.get(
            f"{API_BASE}/api/scout/items?hours=24",
            auth=AUTH
        )
        response.raise_for_status()
        items = response.json()
        initial_count = len(items)
        
        if len(items) < 2:
            print(f"✗ FAILED: Expected at least 2 items, got {len(items)}")
        else:
            # Verify items have required fields
            required_fields = {"id", "title", "link", "raw_source", "fetched_at"}
            all_valid = all(
                all(field in item for field in required_fields)
                for item in items
            )
            if not all_valid:
                print(f"✗ FAILED: Missing required fields in items")
            else:
                print(f"✓ PASSED: Got {len(items)} items with required fields")
                passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
    print()
    
    # Test 5: POST fetch again → verify dedup
    total += 1
    print("5. POST fetch again (should not create duplicates)...")
    try:
        response = requests.post(
            f"{API_BASE}/api/scout/fetch?mode=fixture",
            auth=AUTH
        )
        response.raise_for_status()
        
        # Get items again
        response2 = requests.get(
            f"{API_BASE}/api/scout/items?hours=24",
            auth=AUTH
        )
        response2.raise_for_status()
        items_after = response2.json()
        new_count = len(items_after)
        
        if new_count > initial_count:
            print(f"✗ FAILED: Item count increased ({initial_count} → {new_count}), dedup failed")
        else:
            print(f"✓ PASSED: Item count unchanged ({initial_count}), dedup works")
            passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
    print()
    
    # Test 6: DELETE temp feed (disable)
    total += 1
    print("6. DELETE temp feed (should disable)...")
    try:
        response = requests.delete(
            f"{API_BASE}/api/scout/feeds/{temp_feed_id}",
            auth=AUTH
        )
        response.raise_for_status()
        
        # Verify feed is disabled
        response2 = requests.get(
            f"{API_BASE}/api/scout/feeds",
            auth=AUTH
        )
        response2.raise_for_status()
        feeds = response2.json()
        feed = next((f for f in feeds if f["id"] == temp_feed_id), None)
        
        if not feed:
            print(f"✗ FAILED: Feed not found after delete")
        elif feed["is_enabled"]:
            print(f"✗ FAILED: Feed should be disabled")
        else:
            print(f"✓ PASSED: Feed disabled successfully")
            passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
    print()
    
    # Summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
