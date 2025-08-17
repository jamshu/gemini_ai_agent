"""
Test suite for the Agent class
==============================
"""

import pytest
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import Agent
from src.config import Config, ModelType
from src.conversation import ConversationManager


class TestAgent:
    """Test cases for the Agent class."""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create a test configuration."""
        config = Config()
        config.api_key = os.getenv("GEMINI_API_KEY", "test-key")
        config.data_dir = tmp_path / "data"
        config.cache_dir = tmp_path / "cache"
        config.log_file = tmp_path / "logs" / "test.log"
        return config
    
    @pytest.fixture
    def agent(self, config):
        """Create a test agent instance."""
        return Agent(config)
    
    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent is not None
        assert agent.config is not None
        assert agent.client is not None
        assert agent.conversation is not None
        assert len(agent.tool_functions) > 0
    
    def test_tool_setup(self, agent):
        """Test that tools are properly set up."""
        # Check that essential tools are available
        assert "read_file" in agent.tool_functions
        assert "write_file" in agent.tool_functions
        assert "list_files" in agent.tool_functions
        assert "run_command" in agent.tool_functions
        assert "get_system_info" in agent.tool_functions
        
        # Check that tool schemas are set up
        assert agent.available_tools is not None
    
    def test_metrics_tracking(self, agent):
        """Test metrics tracking."""
        initial_metrics = agent.get_metrics()
        
        assert "total_requests" in initial_metrics
        assert "successful_requests" in initial_metrics
        assert "failed_requests" in initial_metrics
        assert "total_tokens" in initial_metrics
        assert "function_calls" in initial_metrics
        assert initial_metrics["total_requests"] == 0
    
    def test_session_management(self, agent):
        """Test session management."""
        # Create a new session
        agent.reset_session()
        assert agent.conversation.current_session is not None
        
        # Get session ID
        session_id = agent.conversation.current_session.session_id
        assert session_id is not None
        assert len(session_id) > 0
    
    def test_config_updates(self, agent):
        """Test configuration updates."""
        # Update model
        agent.config.model = ModelType.GEMINI_PRO
        assert agent.config.model == ModelType.GEMINI_PRO
        
        # Update temperature
        agent.config.temperature = 0.5
        assert agent.config.temperature == 0.5
    
    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="API key not available")
    def test_simple_request(self, agent):
        """Test a simple request (requires API key)."""
        response = agent.process_request("What is 2 + 2?")
        assert response is not None
        assert len(response) > 0
        
        # Check metrics updated
        metrics = agent.get_metrics()
        assert metrics["total_requests"] == 1
    
    def test_cleanup(self, agent, tmp_path):
        """Test cleanup functionality."""
        # Create a session
        agent.reset_session()
        
        # Perform cleanup
        agent.cleanup()
        
        # Check that metrics file was created
        metrics_file = agent.config.data_dir / "metrics.json"
        # Note: File might not exist if no metrics to save
        
        # Check that config was saved
        config_file = agent.config.data_dir / "config.json"
        assert config_file.exists()


class TestConversation:
    """Test cases for conversation management."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a test conversation manager."""
        return ConversationManager(history_dir=tmp_path / "history")
    
    def test_session_creation(self, manager):
        """Test creating a new session."""
        session = manager.create_session()
        assert session is not None
        assert session.session_id is not None
        assert manager.current_session == session
    
    def test_message_addition(self, manager):
        """Test adding messages to a session."""
        manager.create_session()
        
        # Add user message
        user_msg = manager.add_message("user", "Hello, AI!")
        assert user_msg is not None
        assert user_msg.role == "user"
        assert user_msg.content == "Hello, AI!"
        
        # Add assistant message
        assistant_msg = manager.add_message("assistant", "Hello! How can I help?")
        assert assistant_msg is not None
        assert assistant_msg.role == "assistant"
        
        # Check messages in session
        assert len(manager.current_session.messages) == 2
    
    def test_session_persistence(self, manager, tmp_path):
        """Test saving and loading sessions."""
        # Create session with messages
        session = manager.create_session()
        manager.add_message("user", "Test message")
        manager.add_message("assistant", "Test response")
        
        # Save session
        manager.save_session(session)
        
        # Check file was created
        session_file = tmp_path / "history" / f"{session.session_id}.json"
        assert session_file.exists()
        
        # Load session
        loaded_session = manager.get_session(session.session_id)
        assert loaded_session is not None
        assert len(loaded_session.messages) == 2
    
    def test_search_functionality(self, manager):
        """Test searching through sessions."""
        # Create sessions with different content
        session1 = manager.create_session()
        manager.add_message("user", "Tell me about Python")
        
        manager.create_session()
        manager.add_message("user", "Explain JavaScript")
        
        # Search for Python
        results = manager.search_sessions("Python")
        assert len(results) == 1
        assert results[0].session_id == session1.session_id
        
        # Search for something not present
        results = manager.search_sessions("Ruby")
        assert len(results) == 0


class TestFileTools:
    """Test cases for file tools."""
    
    def test_read_file(self, tmp_path):
        """Test reading a file."""
        from src.tools.file_tools import read_file
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Read the file
        result = read_file(str(test_file))
        assert "content" in result
        assert result["content"] == "Hello, World!"
        assert "file_size" in result
        assert "lines" in result
    
    def test_write_file(self, tmp_path):
        """Test writing a file."""
        from src.tools.file_tools import write_file
        
        test_file = tmp_path / "output.txt"
        content = "Test content\nLine 2"
        
        # Write the file
        result = write_file(str(test_file), content)
        assert result.get("success") is True
        assert test_file.exists()
        assert test_file.read_text() == content
    
    def test_list_files(self, tmp_path):
        """Test listing files."""
        from src.tools.file_tools import list_files
        
        # Create some test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.md").write_text("content3")
        
        # List files
        result = list_files(str(tmp_path))
        assert "files" in result
        assert result["count"] >= 2
        
        # List with pattern
        result = list_files(str(tmp_path), pattern="*.txt")
        assert result["count"] == 1
        
        # List recursively
        result = list_files(str(tmp_path), recursive=True)
        assert result["count"] >= 3
    
    def test_search_files(self, tmp_path):
        """Test searching files."""
        from src.tools.file_tools import search_files
        
        # Create test files
        (tmp_path / "test1.py").write_text("def hello():\n    print('world')")
        (tmp_path / "test2.py").write_text("def goodbye():\n    pass")
        
        # Search by content
        result = search_files(str(tmp_path), content_pattern="hello")
        assert result["results_count"] == 1
        assert "test1.py" in result["results"][0]["file"]
        
        # Search by name
        result = search_files(str(tmp_path), name_pattern="test2")
        assert result["results_count"] == 1


class TestSystemTools:
    """Test cases for system tools."""
    
    def test_run_command(self):
        """Test running a command."""
        from src.tools.system_tools import run_command
        
        # Run a simple command
        result = run_command("echo 'Hello, World!'")
        assert result.get("success") is True
        assert "Hello, World!" in result.get("stdout", "")
    
    def test_get_system_info(self):
        """Test getting system information."""
        from src.tools.system_tools import get_system_info
        
        info = get_system_info()
        assert "platform" in info
        assert "cpu" in info
        assert "memory" in info
        assert "disk" in info
        
        # Check platform info
        platform = info["platform"]
        assert "system" in platform
        assert "python_version" in platform


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
