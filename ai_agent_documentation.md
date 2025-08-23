
# AI Agent Module Documentation

## Module Overview

This module implements an AI agent that can interact with the file system, execute Python code, and generate videos using Google's Gemini API. The agent uses function calling to perform actions based on user prompts.

## File Structure

-   `README.md`: Provides a general overview of the project.
-   `ai_agent/`: Contains the core agent implementation.
    -   `agent_main.py`: Main file for the AI agent.
    -   `requirements.txt`: Lists the dependencies for the ai_agent subdirectory.
    -   `src/`: Source code directory (currently empty).
-   `calculator/`: A simple calculator application used for testing and demonstration.
    -   `README.md`: Calculator README.
    -   `lorem.txt`: Dummy text file.
    -   `main.py`: Calculator application.
    -   `pkg/`: Package directory (currently empty).
    -   `sky_color.txt`: Text file containing color information.
    -   `tests.py`: Tests for the calculator application.
-   `call_function.py`: Handles function calling based on the AI model's response.
-   `circle_area.py`: A simple script to calculate the area and circumference of a circle.
-   `config.py`: Configuration file (currently contains only the working directory).
-   `functions/`: Contains definitions for callable functions.
    -   `get_file_content.py`: Implements the `get_file_content` function.
    -   `get_files_info.py`: Implements the `get_files_info` function.
    -   `run_python.py`: Implements the `run_python` function.
    -   `write_file_content.py`: Implements the `write_file` function.
-   `main.py`: The main entry point for the AI agent application.
-   `prompts.py`: Defines the system prompt for the AI model.
-   `pyproject.toml`: Project configuration file for packaging and dependencies.
-   `requirements.txt`: Lists the dependencies for the project.
-   `tests/`: Contains test files (currently empty).
-   `tests.py`: Test file.
-   `video.py`: A script to generate videos using the Gemini API.

## Key Components

### `main.py`

This file is the main entry point for the AI agent application.

-   **Function:** `main()`
    -   Initializes the Gemini API client.
    -   Parses command-line arguments.
    -   Calls the `generate_content()` function to interact with the AI model.
-   **Function:** `generate_content(client, messages, verbose)`
    -   Iteratively interacts with the Gemini API.
    -   Handles function calls based on the model's response.
    -   Prints the final response from the AI model.

### `call_function.py`

This file handles the execution of functions based on the AI model's response.

-   **Variable:** `available_functions`
    -   Defines the available functions that the AI model can call.
-   **Function:** `call_function(function_call_part, verbose=False)`
    -   Calls the appropriate function based on the function name provided by the AI model.
    -   Passes arguments to the function.
    -   Returns the result of the function call.

### `functions/` directory

This directory contains the implementations of the callable functions.

-   `get_file_content.py`:
    -   **Function:** `get_file_content(working_directory, file_path)`
        -   Reads the content of a file.
        -   Returns the file content.
-   `get_files_info.py`:
    -   **Function:** `get_files_info(working_directory, file_path)`
        -   Lists files and directories within a given path.
        -   Returns a list of file information.
-   `run_python.py`:
    -   **Function:** `run_python_file(working_directory, file_path, args="")`
        -   Runs a Python file.
        -   Returns the output of the Python script.
-   `write_file_content.py`:
    -   **Function:** `write_file(working_directory, file_path, content, overwrite=False)`
        -   Writes content to a file.
        -   Can overwrite existing files.

### `prompts.py`

This file defines the system prompt for the AI model.

-   **Variable:** `system_prompt`
    -   Contains the instructions for the AI model.

### `video.py`

This file demonstrates how to generate videos using the Gemini API.

## Usage

1.  Set the `GEMINI_API_KEY` environment variable.
2.  Run `main.py` with a user prompt as a command-line argument.
    ```bash
    python main.py "your prompt here" [--verbose]
    ```

## Dependencies

-   google-generative-ai
-   python-dotenv

