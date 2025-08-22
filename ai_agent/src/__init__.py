"""
AI Agent - A Professional AI Coding Assistant
==============================================

This package provides a comprehensive AI coding assistant with advanced capabilities
for code analysis, project management, and intelligent task automation.
"""

__version__ = "2.0.0"
__author__ = "AI Agent Team"

from .agent import Agent
from .config import Config
from .conversation import ConversationManager

__all__ = ["Agent", "Config", "ConversationManager"]
