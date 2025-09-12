#!/usr/bin/env python3
"""
Test script for the real subtitle downloading system
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins.subtitle_handler import SubtitleHandler

async def test_subtitle_system():
    """Test the subtitle system with popular movies"""
    
    test_movies = [
        "Avatar 2009",
        "Inception",
        "The Dark Knight",
        "Interstellar"
    ]
    
    handler = SubtitleHandler()
    
    try:
        for movie in test_movies:
            print(f"\n{'='*50}")
            print(f"TESTING: {movie}")
            print(f"{'='*50}")
            
            # Search for subtitles
            results = await handler.search_all_sources(movie, 'en')
            
            if results:
                print(f"SUCCESS: Found {len(results)} subtitle sources")
                
                # Test first result
                first_result = results[0]
                print(f"\nTesting download from: {first_result.get('source')}")
                print(f"   Title: {first_result.get('title')}")
                
                # Download subtitle
                content = await handler.download_subtitle(
                    first_result.get('download_url'),
                    first_result.get('source'),
                    first_result,
                    'en',
                    movie
                )
                
                if content:
                    print(f"SUCCESS: Downloaded {len(content)} characters")
                    
                    # Analyze content
                    lines = content.split('\n')
                    valid_lines = [line for line in lines if line.strip()]
                    
                    print(f"   Total lines: {len(valid_lines)}")
                    
                    # Check if it's real or generated
                    if any('generated automatically' in line.lower() for line in valid_lines):
                        print("   FAILED: This is a GENERATED/FAKE subtitle")
                    else:
                        print("   SUCCESS: This appears to be a REAL subtitle")
                    
                    # Show sample
                    print("\n   Sample content:")
                    for i, line in enumerate(valid_lines[:8]):
                        print(f"   {i+1:2d}: {line}")
                        
                else:
                    print("FAILED: No content downloaded")
            else:
                print("FAILED: No subtitles found")
    
    except Exception as e:
        print(f"ERROR: Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await handler.close_session()
        print(f"\n{'='*50}")
        print("TEST COMPLETED")

if __name__ == "__main__":
    print("SUBTITLE SYSTEM TEST")
    print("Testing real subtitle downloading...")
    asyncio.run(test_subtitle_system())