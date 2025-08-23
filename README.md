# AI Agent

## Description

This project implements an AI agent with advanced capabilities, including processing queries, interacting with AI models, managing conversations, and providing an interactive command-line interface.

## Structure

*   `agent_main.py`: Main entry point for the AI agent.
*   `requirements.txt`: Lists the required Python packages (currently incomplete, should include `toml`).
*   `src/`:
    *   `agent.py`: Contains the `Agent` class for core logic.
    *   `cli.py`: Implements the `InteractiveCLI` class.
    *   `config.py`: Defines the `Config` class for managing settings.
    *   `conversation.py`: Manages conversation history.
    *   `logging_config.py`: Configures logging.
    *   `tools/`: Contains modules for various tools.

## Usage

To run the agent, execute `agent_main.py` with the desired command-line arguments. Use `--help` for more information.

## Dependencies

*   toml (install with `pip install toml`)

## File I/O

The agent provides `write_file` and `read_file` capabilities via function calls.
