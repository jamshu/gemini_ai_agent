"""
Logging Configuration and Management
====================================

Provides comprehensive logging with multiple handlers, formatters, and levels.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to console output.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record):
        # Add color to the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
        
        # Add color to the message based on level
        if levelname in self.COLORS:
            record.msg = f"{self.COLORS[levelname]}{record.msg}{self.RESET}"
        
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs structured JSON logs.
    """
    
    def format(self, record):
        log_obj = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'pathname', 'process', 
                          'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class AgentLogger:
    """
    Centralized logging manager for the AI Agent system.
    
    Features:
    - Multiple log handlers (console, file, rotating)
    - Colored console output
    - Structured JSON logging
    - Performance metrics logging
    - Context-aware logging
    """
    
    def __init__(
        self,
        name: str = "ai_agent",
        level: str = "INFO",
        log_file: Optional[Path] = None,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_json: bool = False,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name
            level: Logging level
            log_file: Path to log file
            enable_console: Enable console output
            enable_file: Enable file output
            enable_json: Enable JSON structured logging
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers = []  # Clear existing handlers
        
        # Console handler with colored output
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, level.upper()))
            
            if not enable_json:
                console_format = ColoredFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            else:
                console_format = StructuredFormatter()
            
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if enable_file and log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(getattr(logging, level.upper()))
            
            if enable_json:
                file_format = StructuredFormatter()
            else:
                file_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
        
        # Performance metrics
        self.metrics: Dict[str, Any] = {
            'function_calls': {},
            'errors': [],
            'warnings': [],
            'performance': {}
        }
    
    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance"""
        return self.logger
    
    def log_function_call(self, function_name: str, args: Dict[str, Any], result: Any = None, duration: float = None):
        """Log a function call with arguments and result"""
        self.metrics['function_calls'][function_name] = self.metrics['function_calls'].get(function_name, 0) + 1
        
        log_data = {
            'function': function_name,
            'args': str(args)[:200],  # Truncate long arguments
        }
        
        if result is not None:
            log_data['result'] = str(result)[:200]
        
        if duration is not None:
            log_data['duration_ms'] = f"{duration * 1000:.2f}"
            
            # Track performance metrics
            if function_name not in self.metrics['performance']:
                self.metrics['performance'][function_name] = []
            self.metrics['performance'][function_name].append(duration)
        
        self.logger.debug(f"Function call: {log_data}")
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log an error with context"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.metrics['errors'].append({
            'timestamp': datetime.now().isoformat(),
            **error_data
        })
        
        self.logger.error(f"Error occurred: {error_data}", exc_info=True)
    
    def log_warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log a warning with additional details"""
        warning_data = {
            'message': message,
            'details': details or {}
        }
        
        self.metrics['warnings'].append({
            'timestamp': datetime.now().isoformat(),
            **warning_data
        })
        
        self.logger.warning(f"{message}: {details}" if details else message)
    
    def log_conversation_turn(self, role: str, content: str, tokens: Optional[int] = None):
        """Log a conversation turn"""
        log_data = {
            'role': role,
            'content_preview': content[:100] + '...' if len(content) > 100 else content,
        }
        
        if tokens:
            log_data['tokens'] = tokens
        
        self.logger.info(f"Conversation: {log_data}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of logged metrics"""
        summary = {
            'total_function_calls': sum(self.metrics['function_calls'].values()),
            'function_call_breakdown': self.metrics['function_calls'],
            'total_errors': len(self.metrics['errors']),
            'total_warnings': len(self.metrics['warnings']),
            'performance_summary': {}
        }
        
        # Calculate performance statistics
        for func_name, durations in self.metrics['performance'].items():
            if durations:
                summary['performance_summary'][func_name] = {
                    'calls': len(durations),
                    'avg_duration_ms': sum(durations) / len(durations) * 1000,
                    'min_duration_ms': min(durations) * 1000,
                    'max_duration_ms': max(durations) * 1000
                }
        
        return summary
    
    def export_metrics(self, output_file: Path):
        """Export metrics to a file"""
        with open(output_file, 'w') as f:
            json.dump(self.get_metrics_summary(), f, indent=2)
        
        self.logger.info(f"Metrics exported to {output_file}")

    def shutdown(self):
        """Shutdown the logger and close all handlers."""
        for handler in self.logger.handlers:
            if hasattr(handler, "close"):
                handler.close()
            self.logger.removeHandler(handler)


# Global logger instance
_logger_instance: Optional[AgentLogger] = None


def setup_logging(
    name: str = "ai_agent",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    **kwargs
) -> AgentLogger:
    """
    Setup and return the global logger instance.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Path to log file
        **kwargs: Additional arguments for AgentLogger
    
    Returns:
        AgentLogger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = AgentLogger(name, level, log_file, **kwargs)
    
    return _logger_instance


def get_logger() -> logging.Logger:
    """Get the global logger instance"""
    if _logger_instance is None:
        setup_logging()
    
    return _logger_instance.get_logger()


def get_agent_logger() -> AgentLogger:
    """Get the AgentLogger instance"""
    if _logger_instance is None:
        setup_logging()
    
    return _logger_instance

