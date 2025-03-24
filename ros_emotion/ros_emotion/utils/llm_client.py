#!/usr/bin/env python3

import os
import json
import time
import logging
import requests
from urllib.parse import urlparse

class LLMClient:
    """
    Client for Large Language Model APIs with OpenAI-compatible interface.
    Supports OpenAI and other providers that implement the OpenAI Chat Completions API.
    """
    
    def __init__(self, node=None):
        """
        Initialize the LLM client with configuration from environment variables
        
        Args:
            node: Optional ROS node for logging
        """
        self.node = node
        
        # Load configuration from environment variables
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.api_host = os.getenv('OPENAI_API_HOST', 'api.openai.com')
        self.api_port = os.getenv('OPENAI_API_PORT', '443')
        self.api_base_path = os.getenv('OPENAI_API_BASE_PATH', '/v1')
        
        # Determine if we're using default OpenAI or another provider
        self.is_openai = self.api_host == 'api.openai.com'
        
        # Build the API URL
        self.base_url = self._build_api_url()
        
        # Set up logging
        self.logger = logging.getLogger('llm_client')
        if node:
            self.log = node.get_logger()
            self.log.info(f"ALAINA: Initialized LLM client with model: {self.model}, host: {self.api_host}")
    
    def _build_api_url(self):
        """Build the complete API URL from components"""
        protocol = "https" if self.api_port == "443" else "http"
        return f"{protocol}://{self.api_host}:{self.api_port}{self.api_base_path}"
    
    def _log_info(self, message):
        """Log info messages to both ROS logger and standard logger"""
        if self.node and hasattr(self, 'log'):
            self.log.info(f"ALAINA: {message}")
        self.logger.info(f"ALAINA: {message}")
    
    def _log_error(self, message):
        """Log error messages to both ROS logger and standard logger"""
        if self.node and hasattr(self, 'log'):
            self.log.error(f"ALAINA: {message}")
        self.logger.error(f"ALAINA: {message}")
    
    def call_chat_completion(self, messages, temperature=0.7, max_tokens=None, 
                            timeout=30, system_prompt=None):
        """
        Call the chat completion API with the given messages
        
        Args:
            messages: List of message dictionaries in OpenAI format
            temperature: Temperature for generation (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            timeout: Timeout for API call in seconds
            system_prompt: Optional system prompt to prepend
            
        Returns:
            Tuple of (response_text, full_response)
        """
        # Format messages, adding system prompt if provided
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)
        
        # Build the API request
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature
        }
        
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        start_time = time.time()
        self._log_info(f"Calling LLM API with {len(formatted_messages)} messages")
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
            response.raise_for_status()
            response_json = response.json()
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            self._log_info(f"LLM API call completed in {elapsed_time:.2f} seconds")
            
            if 'choices' in response_json and len(response_json['choices']) > 0:
                response_text = response_json['choices'][0]['message']['content']
                return response_text, response_json
            else:
                self._log_error(f"Unexpected API response format: {response_json}")
                return "", response_json
                
        except requests.exceptions.RequestException as e:
            self._log_error(f"Error calling LLM API: {str(e)}")
            return "", {"error": str(e)}
            
    def get_model_name(self):
        """Return the current model name"""
        return self.model
        
    def set_model(self, model_name):
        """Set a new model to use"""
        self.model = model_name
        self._log_info(f"Model changed to: {self.model}") 