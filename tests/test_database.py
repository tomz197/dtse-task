import pytest
import sqlite3
import os
from datetime import datetime, timedelta
from src.database import DatabaseManager


class TestDatabaseManager:
    """Tests for DatabaseManager class"""
    
    def test_database_initialization(self, temp_db):
        """Test database initialization and schema creation"""
        db_manager, db_path = temp_db
        conn = db_manager.get_connection()
        
        # Check that database file exists
        assert os.path.exists(db_path)
        
        # Check that schema is created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_tokens'")
        result = cursor.fetchone()
        assert result is not None
        
        # Check table structure
        cursor.execute("PRAGMA table_info(api_tokens)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['id', 'token', 'created_at', 'expires_at', 'is_active']
        assert all(col in columns for col in expected_columns)
    
    def test_create_api_token(self, temp_db):
        """Test creating an API token"""
        db_manager, _ = temp_db
        token = "test_token_12345"
        
        token_id = db_manager.create_api_token(token, None)
        assert token_id is not None
        
        # Verify token was created
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        assert row is not None
        assert row['token'] == token
        assert row['is_active'] == 1
    
    def test_create_api_token_with_expiration(self, temp_db):
        """Test creating an API token with expiration"""
        db_manager, _ = temp_db
        token = "test_token_expires"
        expires_at = datetime.now() + timedelta(days=7)
        
        token_id = db_manager.create_api_token(token, expires_at)
        assert token_id is not None
        
        # Verify token was created with expiration
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        assert row is not None
        assert row['expires_at'] is not None
    
    def test_duplicate_token_creation(self, temp_db):
        """Test that duplicate tokens cannot be created"""
        db_manager, _ = temp_db
        token = "duplicate_token"
        
        db_manager.create_api_token(token, None)
        
        # Try to create duplicate token
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.create_api_token(token, None)
    
    def test_get_api_tokens(self, temp_db):
        """Test retrieving all active API tokens"""
        db_manager, _ = temp_db
        
        # Create multiple tokens
        tokens = [f"token_{i}" for i in range(5)]
        for token in tokens:
            db_manager.create_api_token(token, None)
        
        # Get all tokens
        result = db_manager.get_api_tokens()
        assert len(result) == 5
        
        # Verify all tokens are active
        for token_data in result:
            assert token_data['is_active'] == 1
            assert token_data['token'] in tokens
    
    def test_get_api_tokens_excludes_inactive(self, temp_db):
        """Test that inactive tokens are not returned"""
        db_manager, _ = temp_db
        
        # Create active and inactive tokens
        active_token = "active_token"
        inactive_token = "inactive_token"
        
        db_manager.create_api_token(active_token, None)
        db_manager.create_api_token(inactive_token, None)
        
        # Deactivate one token
        db_manager.deactivate_api_token(inactive_token)
        
        # Get tokens - should only return active one
        result = db_manager.get_api_tokens()
        assert len(result) == 1
        assert result[0]['token'] == active_token
    
    def test_deactivate_api_token(self, temp_db):
        """Test deactivating an API token"""
        db_manager, _ = temp_db
        token = "token_to_deactivate"
        
        db_manager.create_api_token(token, None)
        
        # Deactivate token
        success = db_manager.deactivate_api_token(token)
        assert success is True
        
        # Verify token is deactivated
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM api_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        assert row['is_active'] == 0
    
    def test_deactivate_nonexistent_token(self, temp_db):
        """Test deactivating a token that doesn't exist"""
        db_manager, _ = temp_db
        token = "nonexistent_token"
        
        success = db_manager.deactivate_api_token(token)
        assert success is False
    
    def test_validate_api_token_valid(self, temp_db):
        """Test validating a valid API token"""
        db_manager, _ = temp_db
        token = "valid_token"
        
        db_manager.create_api_token(token, None)
        
        is_valid = db_manager.validate_api_token(token)
        assert is_valid is True
    
    def test_validate_api_token_inactive(self, temp_db):
        """Test validating an inactive token"""
        db_manager, _ = temp_db
        token = "inactive_token"
        
        db_manager.create_api_token(token, None)
        db_manager.deactivate_api_token(token)
        
        is_valid = db_manager.validate_api_token(token)
        assert is_valid is False
    
    def test_validate_api_token_expired(self, temp_db):
        """Test validating an expired token"""
        db_manager, _ = temp_db
        token = "expired_token"
        expires_at = datetime.now() - timedelta(days=1)  # Expired yesterday
        
        db_manager.create_api_token(token, expires_at)
        
        is_valid = db_manager.validate_api_token(token)
        assert is_valid is False
    
    def test_validate_api_token_nonexistent(self, temp_db):
        """Test validating a token that doesn't exist"""
        db_manager, _ = temp_db
        token = "nonexistent_token"
        
        is_valid = db_manager.validate_api_token(token)
        assert is_valid is False
    
    def test_thread_local_connections(self, temp_db):
        """Test that each thread gets its own connection"""
        import threading
        
        db_manager, _ = temp_db
        connections = []
        
        def get_connection():
            conn = db_manager.get_connection()
            connections.append(id(conn))
        
        # Create multiple threads
        threads = [threading.Thread(target=get_connection) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Each thread should have its own connection
        assert len(set(connections)) == 3

