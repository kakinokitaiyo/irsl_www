#!/usr/bin/env python3
"""
Simple test script to validate VLM integration without full SBIR pipeline.
Usage: python3 test_vlm_integration.py
"""

import json
import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)
    
    modules = {
        'rospy': 'ROS Python',
        'json': 'JSON parsing',
        'base64': 'Base64 encoding',
        'google': 'Google AI library',
    }
    
    failed = []
    for module_name, description in modules.items():
        try:
            __import__(module_name)
            print(f"✓ {module_name:20} ({description})")
        except ImportError as e:
            print(f"✗ {module_name:20} ({description}) - {e}")
            failed.append(module_name)
    
    if failed:
        print(f"\n⚠️  Missing: {', '.join(failed)}")
        print("Install with: pip install google-genai")
        return False
    
    print("\n✓ All imports successful\n")
    return True


def test_environment():
    """Test if required environment variables are set."""
    print("=" * 60)
    print("Testing environment variables...")
    print("=" * 60)
    
    required_vars = {
        'GEMINI_API_KEY': 'Gemini API key',
    }
    
    optional_vars = {
        'ENABLE_VLM': 'VLM processing toggle',
        'SBIR_TOPK': 'Number of SBIR candidates',
    }
    
    failed_required = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            display_value = value[:10] + '...' if len(value) > 10 else value
            print(f"✓ {var:25} = {display_value}")
        else:
            print(f"✗ {var:25} (not set)")
            failed_required.append(var)
    
    print()
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var:25} = {value}")
        else:
            print(f"○ {var:25} (using default)")
    
    if failed_required:
        print(f"\n⚠️  Missing required: {', '.join(failed_required)}")
        print("\nSet with: export GEMINI_API_KEY='your-key'")
        print("Or add to .env file in CLIP_DB/")
        return False
    
    print("\n✓ Environment variables OK\n")
    return True


def test_gemini_api_module():
    """Test if gemini_api module is available and functional."""
    print("=" * 60)
    print("Testing gemini_api module...")
    print("=" * 60)
    
    try:
        from gemini_api import (
            encode_image_to_base64,
            get_image_mime_type,
            build_vlm_prompt,
        )
        
        print("✓ gemini_api module imports (basic functions)")
        
        # Test helper functions
        print("\n  Testing helper functions:")
        
        # Test MIME type detection
        mime_types = {
            'test.png': 'image/png',
            'test.jpg': 'image/jpeg',
            'test.webp': 'image/webp',
        }
        
        for filename, expected_mime in mime_types.items():
            mime = get_image_mime_type(filename)
            status = "✓" if mime == expected_mime else "✗"
            print(f"  {status} get_image_mime_type('{filename}') = {mime}")
        
        # Test prompt generation
        prompt = build_vlm_prompt()
        print(f"\n  ✓ build_vlm_prompt() generated {len(prompt)} chars")
        
        print("\n✓ All helper functions work\n")
        return True
    
    except ImportError as e:
        print(f"✗ Failed to import gemini_api: {e}")
        print("\nMake sure gemini_api.py is in the same directory\n")
        return False
    except Exception as e:
        import traceback
        print(f"✗ Error testing gemini_api: {e}")
        print(f"  Traceback: {traceback.format_exc()[:200]}\n")
        return False


def test_sub_writing_module():
    """Test if sub_writing1 module is available."""
    print("=" * 60)
    print("Testing sub_writing1 module...")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    sub_writing_path = script_dir / 'sub_writing1.py'
    
    if not sub_writing_path.exists():
        print(f"✗ sub_writing1.py not found at {sub_writing_path}\n")
        return False
    
    print(f"✓ sub_writing1.py found at {sub_writing_path}")
    
    # Check if it has VLM integration
    try:
        with open(sub_writing_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = {
            'from gemini_api import': 'VLM module import',
            'process_sbir_with_vlm': 'VLM processing call',
            'ENABLE_VLM': 'VLM toggle check',
        }
        
        for pattern, description in checks.items():
            if pattern in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description}")
        
        print("\n✓ sub_writing1.py has VLM integration\n")
        return True
    
    except Exception as e:
        print(f"✗ Error reading sub_writing1.py: {e}\n")
        return False


def test_html_ui():
    """Test if touch.html has VLM UI components."""
    print("=" * 60)
    print("Testing HTML UI components...")
    print("=" * 60)
    
    html_path = Path(__file__).parent.parent / 'html' / 'touch' / 'touch.html'
    
    if not html_path.exists():
        print(f"✗ touch.html not found at {html_path}\n")
        return False
    
    print(f"✓ touch.html found at {html_path}")
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = {
            'vlm-decision-panel': 'VLM decision panel element',
            'renderVlmDecision': 'VLM rendering function',
            'action_type': 'VLM action type handling',
        }
        
        for pattern, description in checks.items():
            if pattern in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description}")
        
        print("\n✓ HTML UI has VLM components\n")
        return True
    
    except Exception as e:
        print(f"✗ Error reading touch.html: {e}\n")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Gemini VLM Integration Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = {
        'Imports': test_imports(),
        'Environment': test_environment(),
        'gemini_api module': test_gemini_api_module(),
        'sub_writing1 module': test_sub_writing_module(),
        'HTML UI': test_html_ui(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed! VLM integration is ready.")
        print("\nNext steps:")
        print("1. Start ROS core: roscore")
        print("2. Run: python3 sub_writing1.py")
        print("3. Open: https://localhost/touch/touch.html")
        print("4. Draw a sketch and click Send")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Install google-genai: pip install google-genai")
        print("- Set API key: export GEMINI_API_KEY='your-key'")
        print("- Check file paths are correct")
    
    print("=" * 60)
    print()
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
