"""
Tests for password_utils module.
"""
import pytest
from unittest.mock import patch, MagicMock
import subprocess

import password_utils


class TestHashSystemPassword:
    """Tests for hash_system_password function."""
    
    def test_empty_password_returns_empty(self):
        """Test that empty password returns empty string."""
        assert password_utils.hash_system_password('') == ''
        assert password_utils.hash_system_password(None) == ''
    
    def test_uses_stdin_for_mkpasswd(self):
        """Test that password is passed via stdin, not command line."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='$6$salt$hash',
                returncode=0
            )
            password_utils.hash_system_password('secret123')
            
            # Verify input parameter is used (stdin)
            call_args = mock_run.call_args
            assert call_args.kwargs.get('input') == 'secret123'
            # Verify password is NOT in command args
            cmd = call_args.args[0]
            assert 'secret123' not in cmd
    
    def test_falls_back_to_openssl(self):
        """Test fallback to openssl when mkpasswd fails."""
        call_count = [0]
        
        def mock_run(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:  # First two mkpasswd attempts fail
                raise FileNotFoundError("mkpasswd not found")
            elif 'rand' in args[0]:  # openssl rand
                return MagicMock(stdout='randomsalt', returncode=0)
            else:  # openssl passwd
                return MagicMock(stdout='$6$randomsalt$hash', returncode=0)
        
        with patch('subprocess.run', side_effect=mock_run):
            result = password_utils.hash_system_password('secret123')
            assert result.startswith('$6$')
    
    def test_raises_on_all_methods_failing(self):
        """Test that RuntimeError is raised when all methods fail."""
        with patch('subprocess.run', side_effect=FileNotFoundError("not found")):
            with pytest.raises(RuntimeError) as exc_info:
                password_utils.hash_system_password('secret123')
            assert 'neither mkpasswd nor openssl' in str(exc_info.value).lower()


class TestValidatePassword:
    """Tests for validate_password function."""
    
    @pytest.mark.parametrize("password,expected", [
        ("validpassword", True),
        ("valid123", True),
        ("valid_pass-word.123", True),
        ("", True),  # Empty allowed
        ("has space", False),
        ("has\ttab", False),
        ("has\nnewline", False),
    ])
    def test_password_validation(self, password, expected):
        """Test password validation rules."""
        assert password_utils.validate_password(password) == expected


class TestGetRequiredPasswords:
    """Tests for get_required_passwords function."""
    
    def test_empty_password_marked_required(self):
        """Test that empty password fields are marked as required."""
        config = {
            'LIVE_USER_PASSWORD_CRYPTED': '',
            'LIVE_ROOT_PASSWORD_CRYPTED': '$6$hash',
        }
        result = password_utils.get_required_passwords(config)
        assert result['USER_PASSWORD'] is True
        assert result['ROOT_PASSWORD'] is False
    
    def test_missing_field_marked_required(self):
        """Test that missing password fields are marked as required."""
        config = {}
        result = password_utils.get_required_passwords(config)
        assert result['USER_PASSWORD'] is True
        assert result['ROOT_PASSWORD'] is True
