"""
Tests for validation_utils module.
"""
import pytest
from unittest.mock import patch, MagicMock

import validation_utils


class TestValidateHostname:
    """Tests for validate_hostname function."""
    
    @pytest.mark.parametrize("hostname,expected", [
        ("valid-hostname", True),
        ("host123", True),
        ("a", True),
        ("minios", True),
        ("my-pc", True),
        ("", True),  # Empty allowed
        ("invalid_hostname", False),  # Underscore not allowed
        ("has space", False),
        ("-startwithdash", False),
        ("endwithdash-", False),
        ("a" * 64, False),  # Too long (max 63)
        ("has.dot", False),  # Dots not allowed in hostname
        ("UPPERCASE", False),  # Must be lowercase
    ])
    def test_hostname_validation(self, hostname, expected):
        """Test hostname validation with various inputs."""
        assert validation_utils.validate_hostname(hostname) == expected


class TestValidateUsername:
    """Tests for validate_username function."""
    
    @pytest.mark.parametrize("username,expected", [
        ("validuser", True),
        ("user123", True),
        ("_user", True),
        ("user_name", True),
        ("user-name", True),
        ("root", True),
        ("", True),  # Empty allowed
        ("Invalid", False),  # Uppercase not allowed
        ("user name", False),  # Space not allowed
        ("123user", False),  # Cannot start with digit
        ("a" * 33, False),  # Too long (max 32)
    ])
    def test_username_validation(self, username, expected):
        """Test username validation with various inputs."""
        assert validation_utils.validate_username(username) == expected


class TestValidateLocales:
    """Tests for validate_locales function."""
    
    def test_valid_single_locale(self):
        """Test validation of single valid locale."""
        with patch.object(validation_utils, 'read_available_locales', 
                         return_value={'en_US.UTF-8', 'ru_RU.UTF-8'}):
            assert validation_utils.validate_locales('en_US.UTF-8') is True
    
    def test_valid_multiple_locales(self):
        """Test validation of multiple valid locales."""
        with patch.object(validation_utils, 'read_available_locales',
                         return_value={'en_US.UTF-8', 'ru_RU.UTF-8', 'de_DE.UTF-8'}):
            assert validation_utils.validate_locales('en_US.UTF-8,ru_RU.UTF-8') is True
    
    def test_invalid_locale(self):
        """Test validation of invalid locale."""
        with patch.object(validation_utils, 'read_available_locales',
                         return_value={'en_US.UTF-8'}):
            assert validation_utils.validate_locales('invalid_LOCALE') is False
    
    def test_empty_locale_allowed(self):
        """Test that empty locale string is allowed."""
        assert validation_utils.validate_locales('') is True


class TestValidateTimezone:
    """Tests for validate_timezone function."""
    
    def test_valid_timezone(self):
        """Test validation of valid timezone."""
        with patch.object(validation_utils, 'read_available_timezones',
                         return_value={'Europe/Moscow', 'America/New_York', 'Etc/UTC'}):
            assert validation_utils.validate_timezone('Europe/Moscow') is True
    
    def test_invalid_timezone(self):
        """Test validation of invalid timezone."""
        with patch.object(validation_utils, 'read_available_timezones',
                         return_value={'Europe/Moscow'}):
            assert validation_utils.validate_timezone('Invalid/Timezone') is False
    
    def test_empty_timezone_allowed(self):
        """Test that empty timezone is allowed."""
        assert validation_utils.validate_timezone('') is True
