#!/usr/bin/env python3

import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ros_emotion.utils.llm_client import LLMClient

def main():
    """
    Test script for the LLM client
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test the LLM client')
    parser.add_argument('--prompt', type=str, help='Prompt to send to the LLM')
    parser.add_argument('--system', type=str, help='System prompt')
    parser.add_argument('--model', type=str, help='Override the model to use')
    parser.add_argument('--host', type=str, help='Override the API host')
    parser.add_argument('--port', type=str, help='Override the API port')
    parser.add_argument('--temperature', type=float, default=0.7, help='Temperature for generation')
    parser.add_argument('--file', type=str, help='Input file with the prompt')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Create the LLM client
    client = LLMClient()
    
    # Override configuration if provided
    if args.model:
        client.model = args.model
        print(f"Using model: {client.model}")
        
    if args.host:
        client.api_host = args.host
        client.base_url = client._build_api_url()
        print(f"Using API host: {client.api_host}")
        
    if args.port:
        client.api_port = args.port
        client.base_url = client._build_api_url()
        print(f"Using API port: {client.api_port}")
    
    # Get the prompt
    prompt = None
    if args.file:
        try:
            with open(args.file, 'r') as f:
                prompt = f.read()
                print(f"Loaded prompt from file: {args.file}")
        except Exception as e:
            print(f"Error loading prompt from file: {e}")
            sys.exit(1)
    elif args.prompt:
        prompt = args.prompt
    else:
        prompt = input("Enter prompt: ")
    
    # Get the system prompt
    system_prompt = args.system if args.system else None
    
    # Call the LLM
    print("\nCalling LLM API...")
    print(f"Base URL: {client.base_url}")
    print(f"Model: {client.model}")
    
    messages = [{"role": "user", "content": prompt}]
    response_text, full_response = client.call_chat_completion(
        messages=messages, 
        temperature=args.temperature,
        system_prompt=system_prompt
    )
    
    # Print the response
    print("\n--- LLM Response ---")
    print(response_text)
    print("\n--- Full API Response ---")
    print(json.dumps(full_response, indent=2))

if __name__ == '__main__':
    main() 