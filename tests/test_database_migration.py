"""
Tests for database migration functionality
"""

import pytest
import sqlite3
import tempfile
import os
from services.chat_service.memory_repository import MemoryRepository


class TestDatabaseMigration:
    """Test database migration functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_conversations.db")
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_migration_adds_missing_columns(self):
        """Test that migration adds missing columns to existing database"""
        # Create a legacy database with old schema (missing updated_at column)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create old schema without updated_at, message_count, token_count
        cursor.execute('''
            CREATE TABLE conversations (
                thread_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Insert some test data
        cursor.execute('''
            INSERT INTO conversations (thread_id, title, created_at)
            VALUES ('test123', 'Test Conversation', '2024-01-01T00:00:00')
        ''')
        
        conn.commit()
        conn.close()
        
        # Initialize memory repository (this should trigger migration)
        repo = MemoryRepository(db_path=self.db_path)
        
        # Verify that missing columns were added
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        assert 'updated_at' in columns
        assert 'message_count' in columns  
        assert 'token_count' in columns
        
        # Verify existing data still exists
        cursor.execute("SELECT thread_id, title FROM conversations WHERE thread_id = 'test123'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == 'test123'
        assert result[1] == 'Test Conversation'
        
        conn.close()
    
    def test_no_migration_needed_for_new_database(self):
        """Test that no migration is needed for new database"""
        # Initialize repository with fresh database
        repo = MemoryRepository(db_path=self.db_path)
        
        # Verify all columns exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        expected_columns = ['thread_id', 'title', 'created_at', 'updated_at', 'message_count', 'token_count']
        for col in expected_columns:
            assert col in columns
        
        conn.close()
    
    def test_migration_sets_default_values(self):
        """Test that migration sets appropriate default values"""
        # Create legacy database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE conversations (
                thread_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            INSERT INTO conversations (thread_id, title, created_at)
            VALUES ('test123', 'Test Conversation', '2024-01-01T00:00:00')
        ''')
        
        conn.commit()
        conn.close()
        
        # Trigger migration
        repo = MemoryRepository(db_path=self.db_path)
        
        # Check that default values were set
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT updated_at, message_count, token_count 
            FROM conversations 
            WHERE thread_id = 'test123'
        ''')
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] is not None  # updated_at should be set
        assert result[1] == 0  # message_count should default to 0
        assert result[2] == 0  # token_count should default to 0
        
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__])