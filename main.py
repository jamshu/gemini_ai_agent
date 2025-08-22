import sys
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from prompts import system_prompt
from call_function import call_function, available_functions


def main():
    load_dotenv()

    verbose = "--verbose" in sys.argv
    args = []
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            args.append(arg)

    if not args:
        print("AI Code Assistant")
        print('\nUsage: python main.py "your prompt here" [--verbose]')
        print('Example: python main.py "How do I fix the calculator?"')
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    user_prompt = " ".join(args)

    if verbose:
        print(f"User prompt: {user_prompt}\n")

    messages = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)]),
    ]

    generate_content(client, messages, verbose)


def generate_content(client, messages, verbose):
    max_iterations = 20
    
    for iteration in range(max_iterations):
        try:
            # Generate content with the current conversation state
            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=[available_functions], system_instruction=system_prompt
                ),
            )
            
            if verbose:
                print(f"\nIteration {iteration + 1}:")
                print("Prompt tokens:", response.usage_metadata.prompt_token_count)
                print("Response tokens:", response.usage_metadata.candidates_token_count)
            
            # Add the model's response (candidates) to the conversation
            for candidate in response.candidates:
                messages.append(types.Content(role="model", parts=candidate.content.parts))
            
            # Handle function calls if present (check this BEFORE checking for text)
            if response.function_calls:
                function_responses = []
                
                for function_call_part in response.function_calls:
                    if verbose:
                        print(f" - Calling function: {function_call_part.name}")
                    
                    function_call_result = call_function(function_call_part, verbose)
                    
                    if (
                        not function_call_result.parts
                        or not function_call_result.parts[0].function_response
                    ):
                        raise Exception("empty function call result")
                    
                    if verbose:
                        print(f"   -> {function_call_result.parts[0].function_response.response}")
                    
                    function_responses.append(function_call_result.parts[0])
                
                # Add function responses to the conversation as a user message
                if function_responses:
                    messages.append(types.Content(role="user", parts=function_responses))
            else:
                # No function calls, check if we have a final text response
                try:
                    if response.text:
                        print("\nFinal response:")
                        print(response.text)
                        return response.text
                except Exception:
                    # response.text might raise an exception in some cases
                    pass
            
        except Exception as e:
            print(f"\nError during iteration {iteration + 1}: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            break
    
    print(f"\nReached maximum iterations ({max_iterations}) without a final response.")
    return None


if __name__ == "__main__":
    main()
