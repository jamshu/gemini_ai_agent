"""
Core Agent Implementation
========================

The main AI Agent class that integrates all components.
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from google import genai
from google.genai import types

from .config import Config
from .conversation import ConversationManager
from .logging_config import setup_logging, get_agent_logger
from .tools.file_tools import (
    read_file, write_file, list_files, search_files,
    schema_read_file, schema_write_file, schema_list_files
)
from .tools.system_tools import (
    run_command, get_system_info, manage_processes,
    schema_run_command, schema_get_system_info, schema_manage_processes
)


class Agent:
    """
    The main AI Agent class that provides intelligent assistance.
    
    Features:
    - Multi-turn conversations with context management
    - Extensive tool integration
    - Error handling and retry logic
    - Performance monitoring
    - Session management
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Agent.
        
        Args:
            config: Configuration object (uses default if not provided)
        """
        self.config = config or Config()
        
        # Setup logging
        self.logger_manager = setup_logging(
            level=self.config.log_level.value,
            log_file=self.config.log_file
        )
        self.logger = self.logger_manager.get_logger()
        
        # Initialize Gemini client
        self.client = genai.Client(api_key=self.config.api_key)
        
        # Initialize conversation manager
        self.conversation = ConversationManager(
            history_dir=self.config.data_dir / "history"
        )
        
        # Setup available tools
        self._setup_tools()
        
        # Performance tracking
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "function_calls": 0,
            "average_response_time": 0
        }
        
        self.logger.info("Agent initialized successfully")
    
    def _setup_tools(self):
        """Setup available tools and their schemas."""
        # Map tool names to functions
        self.tool_functions = {
            # File tools
            "read_file": read_file,
            "write_file": write_file,
            "list_files": list_files,
            "search_files": search_files,
            
            # System tools
            "run_command": run_command,
            "get_system_info": get_system_info,
            "manage_processes": manage_processes,
        }
        
        # Create Gemini tools declaration
        self.available_tools = types.Tool(
            function_declarations=[
                schema_read_file,
                schema_write_file,
                schema_list_files,
                schema_run_command,
                schema_get_system_info,
                schema_manage_processes,
            ]
        )
        
        self.logger.debug(f"Loaded {len(self.tool_functions)} tools")
    
    def process_request(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> str:
        """
        Process a user request.
        
        Args:
            user_input: The user's input/question
            context: Additional context for the request
            stream: Whether to stream the response
        
        Returns:
            The agent's response
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # Add to conversation history
            self.conversation.add_message("user", user_input, metadata=context)
            
            # Get conversation context
            messages = self._prepare_messages(user_input)
            
            # Generate response with retry logic
            response = self._generate_with_retry(messages, stream)
            
            # Update metrics
            elapsed_time = time.time() - start_time
            self._update_metrics(elapsed_time, success=True)
            
            # Log the interaction
            self.logger_manager.log_conversation_turn("user", user_input)
            self.logger_manager.log_conversation_turn("assistant", response)
            
            # Save conversation
            if self.config.enable_history:
                self.conversation.save_session(self.conversation.current_session)
            
            self.metrics["successful_requests"] += 1
            return response
        
        except Exception as e:
            self.metrics["failed_requests"] += 1
            self.logger_manager.log_error(e, {"user_input": user_input})
            
            error_message = f"I encountered an error: {str(e)}. Please try again."
            self.conversation.add_message("assistant", error_message, 
                                        metadata={"error": str(e)})
            return error_message
    
    def _prepare_messages(self, user_input: str) -> List[types.Content]:
        """Prepare messages for the model."""
        messages = []
        
        # Add conversation context if enabled
        if self.config.enable_history:
            context_messages = self.conversation.get_context(max_messages=10)
            messages.extend(context_messages)
        
        # Add current user input
        messages.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
        )
        
        return messages
    
    def _generate_with_retry(
        self,
        messages: List[types.Content],
        stream: bool = False
    ) -> str:
        """
        Generate response with retry logic and tool handling.
        
        Args:
            messages: Conversation messages
            stream: Whether to stream the response
        
        Returns:
            Generated response text
        """
        max_iterations = self.config.max_iterations
        retry_attempts = self.config.retry_attempts
        
        for iteration in range(max_iterations):
            for attempt in range(retry_attempts):
                try:
                    # Generate response
                    response = self.client.models.generate_content(
                        model=self.config.model.value,
                        contents=messages,
                        config=types.GenerateContentConfig(
                            tools=[self.available_tools],
                            system_instruction=self.config.get_system_prompt(
                                list(self.tool_functions.keys())
                            ),
                            temperature=self.config.temperature,
                            max_output_tokens=self.config.max_tokens
                        )
                    )
                    
                    # Log token usage
                    if response.usage_metadata:
                        self.metrics["total_tokens"] += (
                            response.usage_metadata.prompt_token_count +
                            response.usage_metadata.candidates_token_count
                        )
                    
                    # Add response to messages
                    for candidate in response.candidates:
                        messages.append(candidate.content)
                    
                    # Handle function calls
                    if response.function_calls:
                        function_responses = self._handle_function_calls(
                            response.function_calls
                        )
                        
                        # Add function responses to messages
                        if function_responses:
                            messages.append(
                                types.Content(role="user", parts=function_responses)
                            )
                        
                        # Continue to next iteration for more processing
                        continue
                    
                    # Check for final text response
                    if response.text:
                        # Add to conversation history
                        self.conversation.add_message("assistant", response.text)
                        return response.text
                    
                    break  # Exit retry loop if successful
                
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < retry_attempts - 1:
                        time.sleep(self.config.retry_delay * (attempt + 1))
                    else:
                        raise
        
        # If we reach here, no final response was generated
        return "I couldn't generate a complete response. Please try rephrasing your request."
    
    def _handle_function_calls(
        self,
        function_calls: List[Any]
    ) -> List[types.Part]:
        """
        Handle function calls from the model.
        
        Args:
            function_calls: List of function calls from the model
        
        Returns:
            List of function response parts
        """
        responses = []
        
        for function_call in function_calls:
            self.metrics["function_calls"] += 1
            
            function_name = function_call.name
            function_args = dict(function_call.args)
            
            self.logger.info(f"Executing function: {function_name}")
            
            # Execute function
            start_time = time.time()
            
            if function_name in self.tool_functions:
                try:
                    result = self.tool_functions[function_name](**function_args)
                    duration = time.time() - start_time
                    
                    # Log function execution
                    self.logger_manager.log_function_call(
                        function_name, function_args, result, duration
                    )
                    
                    # Create response part
                    responses.append(
                        types.Part.from_function_response(
                            name=function_name,
                            response={"result": result}
                        )
                    )
                
                except Exception as e:
                    self.logger.error(f"Function {function_name} failed: {e}")
                    responses.append(
                        types.Part.from_function_response(
                            name=function_name,
                            response={"error": str(e)}
                        )
                    )
            else:
                self.logger.warning(f"Unknown function: {function_name}")
                responses.append(
                    types.Part.from_function_response(
                        name=function_name,
                        response={"error": f"Unknown function: {function_name}"}
                    )
                )
        
        return responses
    
    def _update_metrics(self, elapsed_time: float, success: bool):
        """Update performance metrics."""
        if success:
            # Update average response time
            total_successful = self.metrics["successful_requests"]
            current_avg = self.metrics["average_response_time"]
            
            self.metrics["average_response_time"] = (
                (current_avg * (total_successful - 1) + elapsed_time) / total_successful
                if total_successful > 0 else elapsed_time
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        metrics = self.metrics.copy()
        metrics.update(self.logger_manager.get_metrics_summary())
        
        if self.conversation.current_session:
            metrics["current_session"] = {
                "id": self.conversation.current_session.session_id,
                "messages": len(self.conversation.current_session.messages),
                "duration": (
                    self.conversation.current_session.updated_at -
                    self.conversation.current_session.created_at
                ).total_seconds()
            }
        
        return metrics
    
    def reset_session(self):
        """Start a new conversation session."""
        self.conversation.create_session()
        self.logger.info("Started new conversation session")
    
    def search_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search conversation history.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching sessions
        """
        sessions = self.conversation.search_sessions(query, limit)
        return [
            {
                "session_id": s.session_id,
                "summary": s.summarize(),
                "messages_count": len(s.messages)
            }
            for s in sessions
        ]
    
    def export_session(
        self,
        session_id: Optional[str] = None,
        format: str = "json"
    ) -> str:
        """
        Export a conversation session.
        
        Args:
            session_id: Session ID (current if not provided)
            format: Export format (json, markdown)
        
        Returns:
            Exported session data
        """
        if not session_id and self.conversation.current_session:
            session_id = self.conversation.current_session.session_id
        
        if not session_id:
            raise ValueError("No session to export")
        
        return self.conversation.export_session(session_id, format)
    
    def cleanup(self):
        """Cleanup resources and save state."""
        # Save current session
        if self.conversation.current_session:
            self.conversation.save_session(self.conversation.current_session)
        
        # Export metrics
        metrics_file = self.config.data_dir / "metrics.json"
        self.logger_manager.export_metrics(metrics_file)
        
        # Save configuration
        self.config.save()
        
        self.logger.info("Agent cleanup completed")
