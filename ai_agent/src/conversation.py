"""
Conversation Management System
==============================

Handles conversation history, context management, and session persistence.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from google.genai import types


@dataclass
class Message:
    """
    Represents a single message in the conversation.
    
    Attributes:
        role: The role of the message sender (user, assistant, system, tool)
        content: The message content
        timestamp: When the message was created
        metadata: Additional metadata about the message
    """
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class ConversationSession:
    """
    Represents a complete conversation session.
    
    Attributes:
        session_id: Unique identifier for the session
        messages: List of messages in the conversation
        created_at: When the session was created
        updated_at: When the session was last updated
        metadata: Session metadata (tags, context, etc.)
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Message):
        """Add a message to the session"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        """Create session from dictionary"""
        data["messages"] = [Message.from_dict(msg) for msg in data["messages"]]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)
    
    def get_context_window(self, max_messages: int = 10) -> List[Message]:
        """Get the most recent messages for context"""
        return self.messages[-max_messages:] if self.messages else []
    
    def summarize(self) -> str:
        """Generate a summary of the conversation"""
        if not self.messages:
            return "Empty conversation"
        
        summary_parts = [
            f"Session ID: {self.session_id[:8]}...",
            f"Messages: {len(self.messages)}",
            f"Duration: {(self.updated_at - self.created_at).total_seconds():.1f}s",
        ]
        
        # Add first and last user messages for context
        user_messages = [msg for msg in self.messages if msg.role == "user"]
        if user_messages:
            summary_parts.append(f"First query: {user_messages[0].content[:50]}...")
            if len(user_messages) > 1:
                summary_parts.append(f"Last query: {user_messages[-1].content[:50]}...")
        
        return " | ".join(summary_parts)


class ConversationManager:
    """
    Manages conversation sessions with persistence and retrieval.
    
    Features:
    - Session creation and management
    - History persistence to disk
    - Context window management
    - Search and retrieval of past conversations
    - Analytics and insights
    """
    
    def __init__(self, history_dir: Optional[Path] = None):
        """
        Initialize the conversation manager.
        
        Args:
            history_dir: Directory to store conversation history
        """
        self.history_dir = history_dir or (Path.home() / ".ai_agent" / "history")
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[ConversationSession] = None
        self.sessions: Dict[str, ConversationSession] = {}
        
        self._load_recent_sessions()
    
    def _load_recent_sessions(self, limit: int = 10):
        """Load recent sessions from disk"""
        session_files = sorted(
            self.history_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        for session_file in session_files:
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    session = ConversationSession.from_dict(session_data)
                    self.sessions[session.session_id] = session
            except Exception as e:
                print(f"Warning: Could not load session {session_file}: {e}")
    
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> ConversationSession:
        """Create a new conversation session"""
        session = ConversationSession(metadata=metadata or {})
        self.sessions[session.session_id] = session
        self.current_session = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get a session by ID"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try to load from disk if not in memory
        session_file = self.history_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    session = ConversationSession.from_dict(session_data)
                    self.sessions[session_id] = session
                    return session
            except Exception:
                pass
        
        return None
    
    def save_session(self, session: ConversationSession):
        """Save a session to disk"""
        session_file = self.history_dir / f"{session.session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the current session"""
        if not self.current_session:
            self.create_session()
        
        message = Message(role=role, content=content, metadata=metadata or {})
        self.current_session.add_message(message)
        return message
    
    def get_context(self, max_messages: int = 10) -> List[types.Content]:
        """Get conversation context in Gemini format"""
        if not self.current_session:
            return []
        
        context_messages = self.current_session.get_context_window(max_messages)
        gemini_messages = []
        
        for msg in context_messages:
            # Convert to Gemini format
            if msg.role in ["user", "model"]:
                gemini_messages.append(
                    types.Content(
                        role=msg.role,
                        parts=[types.Part(text=msg.content)]
                    )
                )
        
        return gemini_messages
    
    def search_sessions(self, query: str, limit: int = 10) -> List[ConversationSession]:
        """Search for sessions containing specific content"""
        matching_sessions = []
        
        for session in self.sessions.values():
            for message in session.messages:
                if query.lower() in message.content.lower():
                    matching_sessions.append(session)
                    break
            
            if len(matching_sessions) >= limit:
                break
        
        return matching_sessions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        total_messages = sum(len(s.messages) for s in self.sessions.values())
        total_sessions = len(self.sessions)
        
        role_counts = {}
        for session in self.sessions.values():
            for message in session.messages:
                role_counts[message.role] = role_counts.get(message.role, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
            "role_distribution": role_counts,
            "oldest_session": min(
                (s.created_at for s in self.sessions.values()),
                default=None
            ),
            "newest_session": max(
                (s.created_at for s in self.sessions.values()),
                default=None
            )
        }
    
    def export_session(self, session_id: str, format: str = "json") -> str:
        """Export a session in various formats"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if format == "json":
            return json.dumps(session.to_dict(), indent=2)
        elif format == "markdown":
            lines = [
                f"# Conversation Session: {session.session_id}",
                f"**Created:** {session.created_at}",
                f"**Updated:** {session.updated_at}",
                "",
                "## Messages",
                ""
            ]
            
            for msg in session.messages:
                lines.append(f"### {msg.role.title()} ({msg.timestamp})")
                lines.append(msg.content)
                lines.append("")
            
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def clear_old_sessions(self, days: int = 30):
        """Clear sessions older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for session_file in self.history_dir.glob("*.json"):
            if session_file.stat().st_mtime < cutoff_date:
                session_file.unlink()
                
                # Remove from memory if loaded
                session_id = session_file.stem
                self.sessions.pop(session_id, None)
