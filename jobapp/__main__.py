#!/usr/bin/env python3
"""
Entry point for running JobApp as a module: python -m jobapp
"""

import asyncio
from .main import main

if __name__ == "__main__":
    asyncio.run(main()) 