#!/usr/bin/env python3
"""Simple test script for SearXNG integration"""

import sys
import os
import requests
import json

def test_searxng_integration():
    """Test SearXNG bang syntax integration"""
    
    base_url = "http://localhost:8888"
    
    print("🔍 Testing SearXNG Bang Syntax Integration")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "All News Engines",
            "query": "!news economy",
            "expected_engines": ["google news", "bing news", "yahoo news"]
        },
        {
            "name": "Yahoo News Only",
            "query": "!yhn breaking news", 
            "expected_engines": ["yahoo news"]
        },
        {
            "name": "DuckDuckGo News Only",
            "query": "!ddn technology trends",
            "expected_engines": ["duckduckgo news"]
        },
        {
            "name": "Reddit Search",
            "query": "!re python programming",
            "expected_engines": ["google"]  # Reddit uses custom Google search
        },
        {
            "name": "Google Search",
            "query": "!go climate change",
            "expected_engines": ["google"]
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test['name']}")
        print(f"Query: {test['query']}")
        
        try:
            params = {
                "q": test['query'],
                "format": "json",
                "pageno": 1
            }
            
            response = requests.get(f"{base_url}/search", params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            print(f"✅ Results found: {len(results)}")
            
            # Show unique engines
            engines = list(set(result.get("engine", "") for result in results))
            print(f"🔧 Engines used: {engines}")
            
            # Show first 2 results
            for j, result in enumerate(results[:2], 1):
                title = result.get("title", "")[:60]
                engine = result.get("engine", "")
                print(f"  {j}. [{engine}] {title}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Available Bang Shortcuts:")
    
    # Test config endpoint
    try:
        config_response = requests.get(f"{base_url}/config", timeout=10)
        config_response.raise_for_status()
        
        config = config_response.json()
        engines = config.get("engines", [])
        
        # Find news engines with shortcuts
        news_engines = []
        for engine in engines:
            categories = engine.get("categories", [])
            if "news" in categories and engine.get("shortcut"):
                news_engines.append({
                    "name": engine.get("name"),
                    "shortcut": engine.get("shortcut"),
                    "enabled": engine.get("enabled", False)
                })
        
        print("\n📰 News Engines:")
        for engine in news_engines:
            status = "✅" if engine["enabled"] else "❌"
            print(f"  {status} {engine['shortcut']} - {engine['name']}")
            
        # Find general engines with shortcuts
        general_engines = []
        for engine in engines:
            categories = engine.get("categories", [])
            if "general" in categories and engine.get("shortcut"):
                general_engines.append({
                    "name": engine.get("name"),
                    "shortcut": engine.get("shortcut"),
                    "enabled": engine.get("enabled", False)
                })
        
        print("\n🌐 General Engines:")
        for engine in general_engines:
            status = "✅" if engine["enabled"] else "❌"
            print(f"  {status} {engine['shortcut']} - {engine['name']}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get config: {e}")
    
    print("\n📖 Usage Examples:")
    print("  !news technology    - All news engines")
    print("  !yhn economy       - Yahoo News only") 
    print("  !ddn breaking      - DuckDuckGo News only")
    print("  !re python         - Reddit search")
    print("  !go climate        - Google search")
    print("  !!w wikipedia      - Wikipedia (external)")

if __name__ == "__main__":
    test_searxng_integration()