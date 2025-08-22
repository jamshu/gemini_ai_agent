"""
Configuration Management System
===============================

Provides centralized configuration management with validation,
environment variable support, and runtime configuration updates.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

class ModelType(Enum):
    """Supported AI model types"""
    GEMINI_FLASH = "gemini-2.0-flash-001"
    GEMINI_PRO = "gemini-1.5-pro"
    GEMINI_FLASH_THINKING = "gemini-2.0-flash-thinking-exp"


class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Config:
    """
    Centralized configuration for the AI Agent system.
    
    Attributes:
        api_key: API key for the AI service
        model: AI model to use
        max_iterations: Maximum conversation iterations
        max_tokens: Maximum tokens per response
        temperature: Model temperature for response generation
        working_dir: Default working directory for file operations
        log_level: Logging verbosity level
        enable_cache: Whether to enable response caching
        cache_dir: Directory for storing cache files
        history_file: Path to conversation history file
        max_file_size: Maximum file size to read (in bytes)
        timeout: Request timeout in seconds
        retry_attempts: Number of retry attempts for failed requests
        interactive_mode: Whether to run in interactive mode
    """
    
    # Core settings
    load_dotenv()
    api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model: ModelType = ModelType.GEMINI_FLASH
    max_iterations: int = 30
    max_tokens: int = 8192
    temperature: float = 0.7
    
    # Directory settings
    working_dir: Path = field(default_factory=lambda: Path.cwd())
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".ai_agent" / "cache")
    data_dir: Path = field(default_factory=lambda: Path.home() / ".ai_agent" / "data")
    
    # Logging settings
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[Path] = field(default_factory=lambda: Path.home() / ".ai_agent" / "logs" / "agent.log")
    
    # Feature flags
    enable_cache: bool = True
    enable_history: bool = True
    enable_auto_fix: bool = True
    enable_code_analysis: bool = True
    
    # File handling
    max_file_size: int = 1024 * 1024 * 10  # 10MB
    max_file_count: int = 100
    allowed_extensions: set = field(default_factory=lambda: {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r",
        ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".xml", ".html",
        ".css", ".scss", ".sass", ".sql", ".sh", ".bash", ".zsh", ".fish"
    })
    
    # Network settings
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Interactive mode settings
    interactive_mode: bool = False
    prompt_style: str = "▶ "
    
    # System prompt customization
    system_prompt_template: str = """You are an advanced AI coding assistant with the following capabilities:

1. **Code Analysis & Understanding**: Analyze code structure, identify patterns, and understand complex codebases
2. **Intelligent Refactoring**: Suggest and implement code improvements following best practices
3. **Project Management**: Create, organize, and manage software projects
4. **Testing & Debugging**: Write tests, identify bugs, and provide fixes
5. **Documentation**: Generate comprehensive documentation and explanations
6. **Learning & Adaptation**: Learn from user preferences and adapt responses accordingly

Guidelines:
- Always prioritize code quality, readability, and maintainability
- Follow language-specific best practices and conventions
- Provide clear explanations for your actions and recommendations
- Ask for clarification when requirements are ambiguous
- Consider performance, security, and scalability in your solutions

Current working directory: {working_dir}
Available tools: {available_tools}
"""
    
    def __post_init__(self):
        """Initialize directories and validate configuration"""
        self._setup_directories()
        self._validate_config()
        self._load_user_config()
    
    def _setup_directories(self):
        """Create necessary directories if they don't exist"""
        for dir_path in [self.cache_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _validate_config(self):
        """Validate configuration values"""
        if not self.api_key:
            raise ValueError("API key is required. Set GEMINI_API_KEY environment variable.")
        
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        
        if self.timeout < 1:
            raise ValueError("timeout must be at least 1 second")
    
    def _load_user_config(self):
        """Load user-specific configuration from file if exists"""
        config_file = self.data_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    self._update_from_dict(user_config)
            except Exception as e:
                print(f"Warning: Could not load user config: {e}")
    
    def _update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        for key, value in config_dict.items():
            if hasattr(self, key):
                if key == "model" and isinstance(value, str):
                    value = ModelType(value)
                elif key == "log_level" and isinstance(value, str):
                    value = LogLevel(value)
                elif key.endswith("_dir") or key.endswith("_file"):
                    value = Path(value) if value else None
                setattr(self, key, value)
    
    def save(self):
        """Save current configuration to file"""
        config_file = self.data_dir / "config.json"
        config_dict = {
            "model": self.model.value,
            "max_iterations": self.max_iterations,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "log_level": self.log_level.value,
            "enable_cache": self.enable_cache,
            "enable_history": self.enable_history,
            "enable_auto_fix": self.enable_auto_fix,
            "enable_code_analysis": self.enable_code_analysis,
            "interactive_mode": self.interactive_mode,
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from a specific file"""
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        config = cls()
        config._update_from_dict(config_dict)
        return config
    
    def get_system_prompt(self, available_tools: list) -> str:
        """Generate system prompt with current configuration"""
        return self.system_prompt_template.format(
            working_dir=self.working_dir,
            available_tools=", ".join(available_tools)
        )
