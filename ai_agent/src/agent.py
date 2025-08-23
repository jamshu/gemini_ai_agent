from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import time
from google import genai
from google.genai import types
from .config import Config
from .conversation import ConversationManager
from .logging_config import setup_logging, get_agent_logger
from .tools.file_tools import (
    read_file, write_file, list_files, search_files,
    create_file, delete_file, move_file, copy_file
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
            "create_file": create_file,
            "delete_file": delete_file,
            "move_file": move_file,
            "copy_file": copy_file,
            
            # System tools
            "run_command": run_command,
            "get_system_info": get_system_info,
            "manage_processes": manage_processes,
        }
        
        # Create function declarations for file tools
        file_tool_declarations = [
            types.FunctionDeclaration(
                name="read_file",
                description="Read file contents with safety checks",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "file_path": types.Schema(type=types.Type.STRING, description="Path to the file"),
                        "encoding": types.Schema(type=types.Type.STRING, description="File encoding (default: utf-8)"),
                        "max_size": types.Schema(type=types.Type.INTEGER, description="Maximum file size to read in bytes")
                    },
                    required=["file_path"]
                )
            ),
            types.FunctionDeclaration(
                name="write_file",
                description="Write content to a file with safety features",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "file_path": types.Schema(type=types.Type.STRING, description="Path to the file"),
                        "content": types.Schema(type=types.Type.STRING, description="Content to write"),
                        "encoding": types.Schema(type=types.Type.STRING, description="File encoding (default: utf-8)"),
                        "create_dirs": types.Schema(type=types.Type.BOOLEAN, description="Create parent directories if needed"),
                        "backup": types.Schema(type=types.Type.BOOLEAN, description="Create backup of existing file")
                    },
                    required=["file_path", "content"]
                )
            ),
            types.FunctionDeclaration(
                name="list_files",
                description="List files in a directory with filtering options",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "directory": types.Schema(type=types.Type.STRING, description="Directory path (default: current directory)"),
                        "pattern": types.Schema(type=types.Type.STRING, description="File pattern to match (default: *)"),
                        "recursive": types.Schema(type=types.Type.BOOLEAN, description="Search recursively"),
                        "include_hidden": types.Schema(type=types.Type.BOOLEAN, description="Include hidden files"),
                        "file_type": types.Schema(type=types.Type.STRING, description="Filter by type: file, dir, or link"),
                        "sort_by": types.Schema(type=types.Type.STRING, description="Sort by: name, size, or modified"),
                        "limit": types.Schema(type=types.Type.INTEGER, description="Maximum number of files to return")
                    },
                    required=[]
                )
            ),
            types.FunctionDeclaration(
                name="search_files",
                description="Search for files matching a pattern",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "directory": types.Schema(type=types.Type.STRING, description="Directory to search in"),
                        "pattern": types.Schema(type=types.Type.STRING, description="File pattern to search for")
                    },
                    required=[]
                )
            ),
        ]
        
        # Create Gemini tools declaration
        self.available_tools = types.Tool(
            function_declarations=[
                *file_tool_declarations,
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
            # Add to conversation history (using 'assistant' for internal storage)
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
            # Convert conversation messages to proper format
            for msg in context_messages:
                try:
                    # Check if it's already a Content object
                    if isinstance(msg, types.Content):
                        # Map roles to valid Gemini API roles
                        if msg.role == "assistant":
                            role = "model"
                        elif msg.role == "user":
                            role = "user"
                        else:
                            # Skip messages with invalid roles
                            self.logger.warning(f"Skipping message with invalid role: {msg.role}")
                            continue
                        
                        # Ensure parts exist and are not empty
                        if msg.parts and len(msg.parts) > 0:
                            # Check if parts have actual content
                            valid_parts = []
                            for part in msg.parts:
                                if hasattr(part, 'text') and part.text and part.text.strip():
                                    valid_parts.append(part)
                                elif hasattr(part, 'function_response') and part.function_response:
                                    valid_parts.append(part)
                            
                            if valid_parts:
                                messages.append(
                                    types.Content(
                                        role=role,
                                        parts=valid_parts
                                    )
                                )
                        else:
                            self.logger.warning("Skipping message with empty parts")
                            
                    elif isinstance(msg, dict):
                        # Handle dictionary format
                        msg_role = msg.get("role", "user")
                        if msg_role == "assistant":
                            role = "model"
                        elif msg_role == "user":
                            role = "user"
                        else:
                            # Skip messages with invalid roles
                            self.logger.warning(f"Skipping message with invalid role: {msg_role}")
                            continue
                            
                        content = msg.get("content", "")
                        if content and str(content).strip():  # Only add non-empty messages
                            messages.append(
                                types.Content(
                                    role=role,
                                    parts=[types.Part(text=str(content).strip())]
                                )
                            )
                    else:
                        # Handle other formats - convert to string and assume user role
                        content_str = str(msg).strip()
                        if content_str:  # Only add non-empty messages
                            messages.append(
                                types.Content(
                                    role="user",
                                    parts=[types.Part(text=content_str)]
                                )
                            )
                except Exception as e:
                    self.logger.warning(f"Error processing message in history: {e}")
                    continue
        
        # Add current user input - ensure it's not empty
        user_input_stripped = user_input.strip()
        if user_input_stripped:
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=user_input_stripped)]
                )
            )
        else:
            # Fallback for empty user input
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text="Hello")]
                )
            )
        
        # Final validation: ensure all messages have valid parts
        validated_messages = []
        for msg in messages:
            if msg.parts and len(msg.parts) > 0:
                # Double-check that at least one part has content
                has_valid_content = False
                for part in msg.parts:
                    if (hasattr(part, 'text') and part.text and part.text.strip()) or \
                       (hasattr(part, 'function_response') and part.function_response):
                        has_valid_content = True
                        break
                
                if has_valid_content:
                    validated_messages.append(msg)
                else:
                    self.logger.warning(f"Skipping message with role '{msg.role}' - no valid content in parts")
            else:
                self.logger.warning(f"Skipping message with role '{msg.role}' - empty or missing parts")
        
        # Ensure we have at least one message
        if not validated_messages:
            validated_messages = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=user_input_stripped or "Hello")]
                )
            ]
        
        # Debug: Log message info for troubleshooting
        message_info = [(msg.role, len(msg.parts), bool(msg.parts[0].text if msg.parts else False)) for msg in validated_messages]
        self.logger.debug(f"Validated {len(validated_messages)} messages: {message_info}")
        
        return validated_messages
    
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
                            response.usage_metadata.prompt_token_count or 0 +
                            response.usage_metadata.candidates_token_count or 0
                        )
                    
                    # Add the model's response to the conversation
                    for candidate in response.candidates:
                        messages.append(types.Content(role="model", parts=candidate.content.parts))
                    
                    # Handle function calls if present (check this BEFORE checking for text)
                    if response.function_calls:
                        function_responses = self._handle_function_calls(response.function_calls)
                        
                        # Add function responses as user message (like in your reference code)
                        if function_responses:
                            messages.append(types.Content(role="user", parts=function_responses))
                        
                        # Continue to next iteration for more processing
                        continue
                    else:
                        # No function calls, check if we have a final text response
                        try:
                            if response.text:
                                # Add to conversation history
                                self.conversation.add_message("assistant", response.text)
                                return response.text
                        except Exception:
                            # response.text might raise an exception in some cases
                            pass
                    
                    break  # Exit retry loop if successful
                
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    
                    # Log detailed error information for debugging
                    if "parts field" in str(e).lower():
                        self.logger.error("Parts validation error detected. Current messages:")
                        for i, msg in enumerate(messages):
                            parts_count = len(msg.parts) if msg.parts else 0
                            self.logger.error(f"  Message {i}: role={msg.role}, parts_count={parts_count}")
                            if msg.parts:
                                for j, part in enumerate(msg.parts):
                                    has_text = hasattr(part, 'text') and bool(part.text)
                                    has_func_resp = hasattr(part, 'function_response') and bool(part.function_response)
                                    self.logger.error(f"    Part {j}: text={has_text}, func_resp={has_func_resp}")
                    
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
        function_responses = []
        
        for function_call_part in function_calls:
            self.metrics["function_calls"] += 1
            
            function_name = function_call_part.name
            function_args = dict(function_call_part.args)
            
            self.logger.info(f"Executing function: {function_name}")
            
            # Execute function
            start_time = time.time()
            
            if function_name in self.tool_functions:
                try:
                    result = self.tool_functions[function_name](**function_args)
                    
                    # Create function response part (similar to your reference code)
                    function_response_part = types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name,
                            response={"result": str(result)}
                        )
                    )
                    function_responses.append(function_response_part)
                    
                except Exception as e:
                    self.logger.error(f"Error executing function {function_name}: {e}")
                    # Create error response
                    function_response_part = types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name,
                            response={"error": f"Error executing function {function_name}: {e}"}
                        )
                    )
                    function_responses.append(function_response_part)
            else:
                error_message = f"Function {function_name} not found."
                self.logger.warning(error_message)
                # Create error response
                function_response_part = types.Part(
                    function_response=types.FunctionResponse(
                        name=function_name,
                        response={"error": error_message}
                    )
                )
                function_responses.append(function_response_part)
            
            elapsed_time = time.time() - start_time
            self.logger.debug(f"Function {function_name} executed in {elapsed_time:.4f}s")
        
        return function_responses
    
    def _update_metrics(self, elapsed_time: float, success: bool = True):
        """Update performance metrics."""
        if success:
            # Update average response time
            total_successful = self.metrics["successful_requests"] + 1
            current_avg = self.metrics["average_response_time"]
            self.metrics["average_response_time"] = (
                (current_avg * (total_successful - 1) + elapsed_time) / total_successful
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.metrics
    
    def export_session(self, session_id: str, format: str = "json") -> str:
        """Export a specific session in the given format."""
        return self.conversation.export_session(session_id, format=format)
    
    def search_history(self, query: str) -> List[Dict[str, Any]]:
        """Search conversation history for a specific query."""
        return self.conversation.search(query)
    
    def cleanup(self):
        """Clean up resources and save any pending data."""
        try:
            # Save current conversation session if history is enabled
            if self.config.enable_history and hasattr(self.conversation, 'current_session'):
                self.conversation.save_session(self.conversation.current_session)
            
            # Close any open file handles in logger
            if hasattr(self.logger_manager, 'cleanup'):
                self.logger_manager.cleanup()
            
            # Log final metrics
            self.logger.info(f"Agent cleanup completed. Final metrics: {self.metrics}")
            
        except Exception as e:
            # Use print as fallback if logger is already closed
            print(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()