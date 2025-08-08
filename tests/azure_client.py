"""
Azure OpenAI client for dynamic chatting during tests.
Provides detailed interaction logging and token tracking.
"""

import os
import time
import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
import openai
from openai import AzureOpenAI

class AzureOpenAIClient:
    """Azure OpenAI client for test interactions."""
    
    def __init__(self):
        """Initialize Azure OpenAI client."""
        self.client = None
        self.is_configured = False
        self.total_tokens_used = 0
        self.total_interactions = 0
        self.interaction_history: List[Dict[str, Any]] = []
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client with environment variables."""
        try:
            # Get Azure OpenAI configuration from environment
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            
            if azure_endpoint and azure_api_key:
                self.client = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=azure_api_key,
                    api_version="2024-02-15-preview"
                )
                self.is_configured = True
                print(f"✅ Azure OpenAI client initialized with deployment: {azure_deployment}")
            else:
                print("⚠️  Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")
                self.is_configured = False
                
        except Exception as e:
            print(f"❌ Failed to initialize Azure OpenAI client: {str(e)}")
            self.is_configured = False
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: str = "gpt-4o",
                       max_tokens: int = 1000,
                       temperature: float = 0.7,
                       test_name: str = "unknown") -> Dict[str, Any]:
        """
        Send chat completion request to Azure OpenAI.
        
        Args:
            messages: List of message dictionaries
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            test_name: Name of the test for logging
            
        Returns:
            Dictionary containing response and interaction details
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Azure OpenAI not configured",
                "response": None,
                "interaction_data": {
                    "test_name": test_name,
                    "timestamp": datetime.now().isoformat(),
                    "duration": 0,
                    "tokens_used": 0,
                    "request": {"messages": messages, "model": model},
                    "response": None
                }
            }
        
        start_time = time.time()
        
        try:
            # Send request to Azure OpenAI
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            duration = time.time() - start_time
            
            # Extract response data
            response_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Update tracking
            self.total_tokens_used += tokens_used
            self.total_interactions += 1
            
            # Create interaction data
            interaction_data = {
                "test_name": test_name,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "tokens_used": tokens_used,
                "request": {
                    "messages": messages,
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                "response": {
                    "content": response_content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "finish_reason": response.choices[0].finish_reason
                }
            }
            
            # Add to history
            self.interaction_history.append(interaction_data)
            
            return {
                "success": True,
                "response": response_content,
                "interaction_data": interaction_data
            }
            
        except Exception as e:
            duration = time.time() - start_time
            error_traceback = traceback.format_exc()
            
            interaction_data = {
                "test_name": test_name,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "tokens_used": 0,
                "request": {
                    "messages": messages,
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                "response": None,
                "error": str(e),
                "error_traceback": error_traceback
            }
            
            return {
                "success": False,
                "error": str(e),
                "error_traceback": error_traceback,
                "response": None,
                "interaction_data": interaction_data
            }
    
    def analyze_test_response(self, 
                            test_name: str,
                            user_query: str,
                            agent_response: str,
                            expected_keywords: List[str] = None) -> Dict[str, Any]:
        """
        Analyze test response using Azure OpenAI.
        
        Args:
            test_name: Name of the test
            user_query: Original user query
            agent_response: Response from the agent
            expected_keywords: Keywords that should be present
            
        Returns:
            Analysis results
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Azure OpenAI not configured",
                "analysis": None
            }
        
        # Create analysis prompt
        analysis_prompt = f"""
        Analyze the following interaction between a user and a legal assistant agent.

        USER QUERY: {user_query}
        AGENT RESPONSE: {agent_response}

        Please analyze this interaction and provide:
        1. Response Quality (1-10): Rate the overall quality and appropriateness
        2. Legal Focus: Does the response stay focused on legal assistance?
        3. Keyword Presence: Are relevant legal keywords present?
        4. Professional Tone: Is the tone appropriate for legal consultation?
        5. Redirection Effectiveness: If user asked non-legal question, was redirection effective?
        6. Specific Issues: Any specific problems or concerns?
        7. Recommendations: Suggestions for improvement

        Expected Keywords: {expected_keywords or []}

        Provide your analysis in JSON format:
        {{
            "response_quality": 8,
            "legal_focus": true,
            "keyword_presence": true,
            "professional_tone": true,
            "redirection_effective": true,
            "issues": [],
            "recommendations": [],
            "overall_assessment": "positive/negative/mixed"
        }}
        """
        
        messages = [
            {"role": "system", "content": "You are an expert legal consultant analyzing AI assistant responses."},
            {"role": "user", "content": analysis_prompt}
        ]
        
        result = self.chat_completion(
            messages=messages,
            test_name=f"{test_name}_analysis",
            max_tokens=500,
            temperature=0.3
        )
        
        if result["success"]:
            try:
                # Try to parse JSON response
                analysis = json.loads(result["response"])
                return {
                    "success": True,
                    "analysis": analysis,
                    "interaction_data": result["interaction_data"]
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "analysis": {"raw_response": result["response"]},
                    "interaction_data": result["interaction_data"]
                }
        else:
            return result
    
    def generate_test_scenario(self, 
                             scenario_type: str,
                             test_name: str) -> Dict[str, Any]:
        """
        Generate test scenarios using Azure OpenAI.
        
        Args:
            scenario_type: Type of scenario to generate
            test_name: Name of the test
            
        Returns:
            Generated scenario
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Azure OpenAI not configured",
                "scenario": None
            }
        
        scenario_prompts = {
            "legal_query": "Generate a realistic legal query in Arabic that a user might ask about their statement of claim.",
            "non_legal_query": "Generate a non-legal query in Arabic that should be redirected to legal assistance.",
            "attachment_query": "Generate a query in Arabic asking about what attachments are needed for a legal case.",
            "complex_legal": "Generate a complex legal question in Arabic about statement of claim procedures."
        }
        
        prompt = scenario_prompts.get(scenario_type, "Generate a test query in Arabic.")
        
        messages = [
            {"role": "system", "content": "You are an expert in generating realistic test scenarios for legal AI assistants."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(
            messages=messages,
            test_name=f"{test_name}_scenario_generation",
            max_tokens=200,
            temperature=0.7
        )
        
        return result
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for all interactions."""
        return {
            "total_interactions": self.total_interactions,
            "total_tokens_used": self.total_tokens_used,
            "average_tokens_per_interaction": self.total_tokens_used / self.total_interactions if self.total_interactions > 0 else 0,
            "is_configured": self.is_configured,
            "interaction_history": self.interaction_history
        }
    
    def reset_usage(self):
        """Reset usage tracking."""
        self.total_tokens_used = 0
        self.total_interactions = 0
        self.interaction_history = []
    
    def export_interactions(self, filename: str = None) -> str:
        """Export interaction history to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"azure_interactions_{timestamp}.json"
        
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "usage_summary": self.get_usage_summary(),
            "interactions": self.interaction_history
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filename

# Global Azure OpenAI client instance
azure_client = AzureOpenAIClient() 