"""
Pytest fixtures for minios-configurator tests.
"""
import os
import sys
import pytest
import tempfile
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python3-minios-security'))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def tmp_path(tmpdir):
    """Provide pathlib temporary paths on pytest versions before 3.9."""
    return Path(str(tmpdir))


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample config file for testing."""
    config_content = '''# MiniOS configuration
LIVE_USER_NAME="user"
LIVE_USER_PASSWORD_CRYPTED=""
LIVE_HOSTNAME="minios"
LIVE_TIMEZONE="Etc/UTC"
LIVE_LOCALES="en_US.UTF-8"
DEFAULT_TARGET="graphical"
'''
    config_path = os.path.join(temp_dir, 'config.conf')
    with open(config_path, 'w') as f:
        f.write(config_content)
    return config_path
