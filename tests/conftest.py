"""
Tests configuration and fixtures
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_logger():
    """Provide mock logger for tests."""
    from unittest.mock import MagicMock
    return MagicMock()


# Make pytest asyncio markers work
pytest_plugins = ('pytest_asyncio',)
