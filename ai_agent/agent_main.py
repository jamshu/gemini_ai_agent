#!/usr/bin/env python3
"""
AI Agent - Main Entry Point
===========================

Professional AI coding assistant with advanced capabilities.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
import os
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import Agent  # Assuming this exists
from src.config import Config  # Assuming this exists
from src.cli import InteractiveCLI  # Assuming this exists


# Simplified call_function and available_functions for file I/O
def call_function(function_call_part, verbose=False):
    """Calls a function based on the function call part."""
    name = function_call_part.name
    arguments = json.loads(function_call_part.args)

    if verbose:
        print(f"Calling function: {name} with arguments: {arguments}")

    if name == "write_file":
        try:
            file_path = arguments["file_path"]
            content = arguments["content"]
            result = default_api.write_file(file_path=file_path, content=content)
            response = {"response": f"File written successfully to {file_path}"}
            return response
        except Exception as e:
            response = {"response": f"Error writing file: {e}"}
            return response
    elif name == "read_file":
        try:
            file_path = arguments["file_path"]
            result = default_api.get_file_content(file_path=file_path)
            content = result['get_file_content_response']['result']
            response = {"response": content}
            return response
        except Exception as e:
            response = {"response": f"Error reading file: {e}"}
            return response
    else:
        response = {"response": f"Function {name} not supported"}
        return response


available_functions = {
    "write_file": {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write to",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
    },
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads content from a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read from",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
}


def main():
    """Main entry point for the AI Agent."""
    parser = argparse.ArgumentParser(
        description="AI Agent - Professional AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python agent.py

  # Single query
  python agent.py "explain this code" --file main.py

  # Write to file
  python agent.py "write hello world to test.txt" --write_file test.txt --content "hello world"

  # With custom model
  python agent.py "refactor this function" --model gemini-1.5-pro

  # Export metrics
  python agent.py --export-metrics
        """
    )

    # Query argument
    parser.add_argument(
        "query",
        nargs="?",
        help="Query to process (interactive mode if not provided)"
    )

    # Configuration options
    parser.add_argument(
        "--model",
        choices=["gemini-2.0-flash-001", "gemini-1.5-pro"],
        help="AI model to use"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        metavar="T",
        help="Temperature for response generation (0.0-2.0)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        metavar="N",
        help="Maximum conversation iterations"
    )

    # File operations
    parser.add_argument(
        "--file",
        type=str,
        help="File to include in context"
    )
    parser.add_argument(
        "--dir",
        type=str,
        help="Working directory"
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file for response"
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format"
    )

    # Utility options
    parser.add_argument(
        "--export-metrics",
        action="store_true",
        help="Export performance metrics"
    )
    parser.add_argument(
        "--export-session",
        metavar="ID",
        help="Export specific session"
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        help="Search conversation history"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )

    # write_file argument
    parser.add_argument(
        "--write_file",
        type=str,
        help="Path to the file to write to"
    )
    parser.add_argument(
        "--content",
        type=str,
        help="Content to write to the file"
    )
    # read_file argument
    parser.add_argument(
        "--read_file",
        type=str,
        help="Path to the file to read from"
    )

    # Logging options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    try:
        # Load configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config()

        # Apply command-line overrides
        if args.model:
            from src.config import ModelType
            config.model = ModelType(args.model)

        if args.temperature is not None:
            if 0 <= args.temperature <= 2:
                config.temperature = args.temperature
            else:
                print("Error: Temperature must be between 0 and 2")
                sys.exit(1)

        if args.max_iterations:
            config.max_iterations = args.max_iterations

        if args.dir:
            config.working_dir = args.dir

        if args.debug:
            from src.config import LogLevel
            config.log_level = LogLevel.DEBUG
        elif args.verbose:
            from src.config import LogLevel
            config.log_level = LogLevel.INFO

        # Create agent
        agent = Agent(config)

        # Handle utility operations
        if args.export_metrics:
            metrics = agent.get_metrics()
            import json
            output = json.dumps(metrics, indent=2)

            if args.output:
                args.output.write_text(output)
                print(f"Metrics exported to {args.output}")
            else:
                print(output)
            return

        if args.export_session:
            try:
                output = agent.export_session(args.export_session, format="json")
                if args.output:
                    args.output.write_text(output)
                    print(f"Session exported to {args.output}")
                else:
                    print(output)
            except Exception as e:
                print(f"Error exporting session: {e}")
                sys.exit(1)
            return

        if args.search:
            results = agent.search_history(args.search)
            if results:
                print(f"Found {len(results)} matching sessions:")
                for result in results:
                    print(f"  - {result['session_id']}: {result['summary']}\n")
            else:
                print(f"No results found for: {args.search}")
            return

        # Process query or start interactive mode
        if args.query:
            # Single query mode
            context = {}

            # Add file context if provided
            if args.file:
                #context["file"] = str(args.file)
                #context["file_content"] = args.file.read_text()
                function_call_part = type('obj', (object,), {'name': 'read_file', 'args': json.dumps({'file_path': args.file})})()
                file_content_response = call_function(function_call_part, verbose=args.verbose)
                if file_content_response:
                  context["file_content"] = file_content_response["response"]
                else:
                  print(f"Error reading file {args.file}")
                  sys.exit(1)

            # Process query
            # response = agent.process_request(args.query, context)  #Original

            # Here's the modified part to handle write_file and read_file
            if args.write_file and args.content:
                # Call write_file function directly
                function_call_part = type('obj', (object,), {'name': 'write_file', 'args': json.dumps({'file_path': args.write_file, 'content': args.content})})()
                function_response = call_function(function_call_part, verbose=args.verbose)
                print(function_response["response"]) # Print response
                response = None # Set response to None so the next section will be skipped
            elif args.read_file:
                # Call read_file function directly
                function_call_part = type('obj', (object,), {'name': 'read_file', 'args': json.dumps({'file_path': args.read_file})})()
                function_response = call_function(function_call_part, verbose=args.verbose)
                print(function_response["response"])  # Print response
                response = None # Set response to None so the next section will be skipped
            else:
                response = agent.process_request(args.query, context)

            if response:
                if args.output:
                    if args.format == "json":
                        output = json.dumps(response, indent=2)
                    else:
                        output = response["response"]
                    with open(args.output, "w") as f:
                        f.write(output)
                    print(f"Response written to {args.output}")
                else:
                    print(response["response"])

        else:
            # Interactive mode
            cli = InteractiveCLI(agent)
            cli.run()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# The following code should be placed within the _generate_with_retry function in src/agent.py, replacing the original line.
# total_tokens += response.usage_metadata.prompt_token_count + response.usage_metadata.completion_token_count
# total_tokens += (response.usage_metadata.prompt_token_count or 0) + (response.usage_metadata.completion_token_count or 0)

if __name__ == "__main__":
    main()
