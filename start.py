#!/usr/bin/env python3
"""
Simple startup script for Movie Bot
"""
import os
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Start bot
if __name__ == "__main__":
    try:
        from bot import Bot
        print("Starting Movie Bot...")
        Bot().run()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Bot failed to start: {e}")
        sys.exit(1)