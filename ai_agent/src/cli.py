"""
Interactive CLI Interface
========================

Provides an interactive command-line interface for the AI Agent.
"""

import sys
import os
import readline
import atexit
from pathlib import Path
from typing import Optional, List, Tuple
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from .agent import Agent
from .config import Config


class InteractiveCLI:
    """
    Interactive command-line interface for the AI Agent.
    
    Features:
    - Rich text formatting
    - Command history
    - Auto-completion
    - Special commands
    - Progress indicators
    """
    
    def __init__(self, agent: Optional[Agent] = None):
        """
        Initialize the CLI.
        
        Args:
            agent: Agent instance (creates new if not provided)
        """
        self.agent = agent or Agent()
        self.console = Console()
        self.running = False
        
        # Setup command history
        self.history_file = Path.home() / ".ai_agent" / "cli_history"
        self._setup_history()
        
        # Special commands
        self.commands = {
            "/help": self._show_help,
            "/exit": self._exit,
            "/quit": self._exit,
            "/clear": self._clear_screen,
            "/reset": self._reset_session,
            "/history": self._show_history,
            "/metrics": self._show_metrics,
            "/config": self._show_config,
            "/save": self._save_session,
            "/load": self._load_session,
            "/search": self._search_history,
            "/export": self._export_session,
            "/model": self._change_model,
            "/temperature": self._change_temperature,
            "/system": self._show_system_info,
        }
        
        # Setup auto-completion
        self._setup_autocomplete()
    
    def _setup_history(self):
        """Setup command history."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load history if exists
        if self.history_file.exists():
            readline.read_history_file(self.history_file)
        
        # Set history length
        readline.set_history_length(1000)
        
        # Save history on exit
        atexit.register(lambda: readline.write_history_file(self.history_file))
    
    def _setup_autocomplete(self):
        """Setup auto-completion for commands."""
        def completer(text: str, state: int) -> Optional[str]:
            options = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]
            
            if state < len(options):
                return options[state]
            return None
        
        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")
    
    def run(self):
        """Run the interactive CLI."""
        self.running = True
        self._show_welcome()
        
        while self.running:
            try:
                # Get user input
                user_input = self._get_input()
                
                if not user_input:
                    continue
                
                # Check for special commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                else:
                    # Process with agent
                    self._process_query(user_input)
            
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit to quit[/yellow]")
                continue
            except EOFError:
                self._exit()
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def _show_welcome(self):
        """Show welcome message."""
        welcome_text = """
# 🤖 AI Agent - Interactive Mode

Welcome to the AI Agent interactive interface!

## Available Commands:
- `/help` - Show this help message
- `/exit` or `/quit` - Exit the application
- `/clear` - Clear the screen
- `/reset` - Start a new conversation
- `/history` - Show conversation history
- `/metrics` - Show performance metrics
- `/config` - Show current configuration
- `/search <query>` - Search conversation history
- `/export [format]` - Export current session
- `/model <model>` - Change the AI model
- `/temperature <value>` - Change temperature setting
- `/system` - Show system information

Type your question or command to get started!
        """
        
        self.console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))
    
    def _get_input(self) -> str:
        """Get user input with rich formatting."""
        try:
            # Show prompt
            prompt = f"\n[bold cyan]{self.agent.config.prompt_style}[/bold cyan]"
            return Prompt.ask(prompt, console=self.console).strip()
        except KeyboardInterrupt:
            return ""
    
    def _handle_command(self, command: str):
        """Handle special commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in self.commands:
            self.commands[cmd](args)
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("[yellow]Type /help for available commands[/yellow]")
    
    def _process_query(self, query: str):
        """Process a query with the agent."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Thinking...", total=None)
            
            try:
                # Get response from agent
                response = self.agent.process_request(query)
                
                # Display response with formatting
                self._display_response(response)
            
            except Exception as e:
                self.console.print(f"[red]Error processing query: {e}[/red]")
    
    def _display_response(self, response: str):
        """Display agent response with rich formatting."""
        # Check if response contains code
        if "```" in response:
            self._display_with_code_blocks(response)
        else:
            # Display as markdown
            self.console.print(Panel(
                Markdown(response),
                title="Assistant",
                border_style="green",
                padding=(1, 2)
            ))
    
    def _display_with_code_blocks(self, response: str):
        """Display response with syntax-highlighted code blocks."""
        parts = response.split("```")
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Regular text
                if part.strip():
                    self.console.print(Markdown(part))
            else:
                # Code block
                lines = part.split("\n", 1)
                language = lines[0].strip() if lines[0].strip() else "text"
                code = lines[1] if len(lines) > 1 else part
                
                self.console.print(Syntax(
                    code.strip(),
                    language,
                    theme="monokai",
                    line_numbers=True
                ))
    
    def _show_help(self, args: str = ""):
        """Show help message."""
        help_text = """
## Commands Reference

### Basic Commands
- `/help` - Show this help message
- `/exit`, `/quit` - Exit the application
- `/clear` - Clear the screen

### Conversation Management
- `/reset` - Start a new conversation session
- `/history` - Show recent conversation history
- `/save [name]` - Save current session with optional name
- `/load <session_id>` - Load a previous session

### Search and Export
- `/search <query>` - Search through conversation history
- `/export [format]` - Export session (json/markdown)

### Configuration
- `/config` - Show current configuration
- `/model <model>` - Change AI model
- `/temperature <0.0-2.0>` - Adjust creativity level

### Information
- `/metrics` - Show performance metrics
- `/system` - Show system information

### Tips
- Use Tab for command auto-completion
- Use Up/Down arrows to navigate history
- Press Ctrl+C to cancel current operation
        """
        
        self.console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))
    
    def _exit(self, args: str = ""):
        """Exit the application."""
        if Confirm.ask("\n[yellow]Are you sure you want to exit?[/yellow]"):
            self.console.print("[green]Goodbye! 👋[/green]")
            self.agent.cleanup()
            self.running = False
            sys.exit(0)
    
    def _clear_screen(self, args: str = ""):
        """Clear the screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def _reset_session(self, args: str = ""):
        """Reset the conversation session."""
        if Confirm.ask("[yellow]Start a new conversation session?[/yellow]"):
            self.agent.reset_session()
            self.console.print("[green]✓ New session started[/green]")
    
    def _show_history(self, args: str = ""):
        """Show conversation history."""
        if not self.agent.conversation.current_session:
            self.console.print("[yellow]No active session[/yellow]")
            return
        
        messages = self.agent.conversation.current_session.messages[-10:]
        
        if not messages:
            self.console.print("[yellow]No messages in current session[/yellow]")
            return
        
        table = Table(title="Recent Conversation History")
        table.add_column("Time", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Message", style="white", overflow="fold")
        
        for msg in messages:
            time_str = msg.timestamp.strftime("%H:%M:%S")
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            table.add_row(time_str, msg.role.title(), content)
        
        self.console.print(table)
    
    def _show_metrics(self, args: str = ""):
        """Show performance metrics."""
        metrics = self.agent.get_metrics()
        
        table = Table(title="Performance Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        # Basic metrics
        table.add_row("Total Requests", str(metrics.get("total_requests", 0)))
        table.add_row("Successful Requests", str(metrics.get("successful_requests", 0)))
        table.add_row("Failed Requests", str(metrics.get("failed_requests", 0)))
        table.add_row("Total Tokens Used", f"{metrics.get('total_tokens', 0):,}")
        table.add_row("Function Calls", str(metrics.get("function_calls", 0)))
        table.add_row("Avg Response Time", f"{metrics.get('average_response_time', 0):.2f}s")
        
        # Session info
        if "current_session" in metrics:
            session = metrics["current_session"]
            table.add_row("Session Messages", str(session["messages"]))
            table.add_row("Session Duration", f"{session['duration']:.1f}s")
        
        self.console.print(table)
    
    def _show_config(self, args: str = ""):
        """Show current configuration."""
        config = self.agent.config
        
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Model", config.model.value)
        table.add_row("Temperature", f"{config.temperature:.1f}")
        table.add_row("Max Iterations", str(config.max_iterations))
        table.add_row("Max Tokens", f"{config.max_tokens:,}")
        table.add_row("Working Directory", str(config.working_dir))
        table.add_row("Cache Enabled", "✓" if config.enable_cache else "✗")
        table.add_row("History Enabled", "✓" if config.enable_history else "✗")
        table.add_row("Auto-fix Enabled", "✓" if config.enable_auto_fix else "✗")
        
        self.console.print(table)
    
    def _save_session(self, args: str = ""):
        """Save current session."""
        if not self.agent.conversation.current_session:
            self.console.print("[yellow]No active session to save[/yellow]")
            return
        
        self.agent.conversation.save_session(self.agent.conversation.current_session)
        session_id = self.agent.conversation.current_session.session_id
        self.console.print(f"[green]✓ Session saved: {session_id}[/green]")
    
    def _load_session(self, args: str):
        """Load a previous session."""
        if not args:
            self.console.print("[red]Please provide a session ID[/red]")
            return
        
        session = self.agent.conversation.get_session(args.strip())
        if session:
            self.agent.conversation.current_session = session
            self.console.print(f"[green]✓ Loaded session: {session.session_id}[/green]")
            self.console.print(f"Messages: {len(session.messages)}")
        else:
            self.console.print(f"[red]Session not found: {args}[/red]")
    
    def _search_history(self, args: str):
        """Search conversation history."""
        if not args:
            self.console.print("[red]Please provide a search query[/red]")
            return
        
        results = self.agent.search_history(args)
        
        if not results:
            self.console.print(f"[yellow]No results found for: {args}[/yellow]")
            return
        
        table = Table(title=f"Search Results for: {args}")
        table.add_column("Session ID", style="cyan")
        table.add_column("Summary", style="white")
        table.add_column("Messages", style="green")
        
        for result in results:
            table.add_row(
                result["session_id"][:8] + "...",
                result["summary"],
                str(result["messages_count"])
            )
        
        self.console.print(table)
    
    def _export_session(self, args: str = ""):
        """Export current session."""
        format_type = args.strip() or "json"
        
        if format_type not in ["json", "markdown"]:
            self.console.print("[red]Invalid format. Use 'json' or 'markdown'[/red]")
            return
        
        try:
            exported = self.agent.export_session(format=format_type)
            
            # Save to file
            filename = f"session_export.{format_type}"
            with open(filename, 'w') as f:
                f.write(exported)
            
            self.console.print(f"[green]✓ Session exported to {filename}[/green]")
        
        except Exception as e:
            self.console.print(f"[red]Export failed: {e}[/red]")
    
    def _change_model(self, args: str):
        """Change the AI model."""
        if not args:
            # Show available models
            self.console.print("[cyan]Available models:[/cyan]")
            for model in ["gemini-2.0-flash-001", "gemini-1.5-pro"]:
                current = " (current)" if model == self.agent.config.model.value else ""
                self.console.print(f"  - {model}{current}")
            return
        
        # Change model
        try:
            from .config import ModelType
            self.agent.config.model = ModelType(args.strip())
            self.console.print(f"[green]✓ Model changed to: {args}[/green]")
        except ValueError:
            self.console.print(f"[red]Invalid model: {args}[/red]")
    
    def _change_temperature(self, args: str):
        """Change temperature setting."""
        if not args:
            self.console.print(f"[cyan]Current temperature: {self.agent.config.temperature}[/cyan]")
            return
        
        try:
            temp = float(args)
            if 0 <= temp <= 2:
                self.agent.config.temperature = temp
                self.console.print(f"[green]✓ Temperature set to: {temp}[/green]")
            else:
                self.console.print("[red]Temperature must be between 0 and 2[/red]")
        except ValueError:
            self.console.print("[red]Invalid temperature value[/red]")
    
    def _show_system_info(self, args: str = ""):
        """Show system information."""
        from .tools.system_tools import get_system_info
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("Getting system info...", total=None)
            info = get_system_info()
        
        if "error" in info:
            self.console.print(f"[red]Error: {info['error']}[/red]")
            return
        
        # Display system info
        table = Table(title="System Information")
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="white")
        
        # Platform info
        platform = info["platform"]
        table.add_row("System", f"{platform['system']} {platform['release']}")
        table.add_row("Machine", platform['machine'])
        table.add_row("Python", platform['python_version'])
        
        # CPU info
        cpu = info["cpu"]
        table.add_row("CPU Cores", f"{cpu['physical_cores']} physical, {cpu['logical_cores']} logical")
        table.add_row("CPU Usage", f"{cpu['usage_percent']:.1f}%")
        
        # Memory info
        memory = info["memory"]
        table.add_row("Memory", f"{memory['used_human']} / {memory['total_human']} ({memory['percent']:.1f}%)")
        
        # Disk info
        disk = info["disk"]
        table.add_row("Disk", f"{disk['used_human']} / {disk['total_human']} ({disk['percent']:.1f}%)")
        
        self.console.print(table)
