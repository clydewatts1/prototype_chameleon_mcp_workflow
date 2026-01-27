#!/usr/bin/env python3
"""
AI Agent for Chameleon Workflow Engine

This agent demonstrates AI-powered processing using Ollama in the Chameleon system.
It polls for work from the "AI_Analyzer" role, calls the Ollama API to generate
a summary of the input text, and submits the result.

Prerequisites:
    - Ollama installed and running locally: https://ollama.ai
    - Model downloaded: ollama pull llama3 (or your preferred model)

Usage:
    python examples/ai_agent.py --base-url http://localhost:8000
    python examples/ai_agent.py --role-id <UUID> --ollama-url http://localhost:11434
"""

import argparse
import sys
import time
import uuid
import requests
from typing import Dict, Any, Optional
import json


class AIAgent:
    """AI Agent for LLM-powered text analysis using Ollama"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        ollama_url: str = "http://localhost:11434",
        role_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        model: str = "llama3",
        poll_interval: int = 5,
    ):
        """
        Initialize the AI Agent.

        Args:
            base_url: Base URL of the Chameleon Workflow Engine server
            ollama_url: Base URL of the Ollama API server
            role_id: UUID of the AI_Analyzer role (if known)
            actor_id: UUID of the AI actor (generated if not provided)
            model: Ollama model to use for generation
            poll_interval: Seconds to wait between polling attempts
        """
        self.base_url = base_url.rstrip("/")
        self.ollama_url = ollama_url.rstrip("/")
        self.role_id = role_id
        self.actor_id = actor_id or str(uuid.uuid4())
        self.model = model
        self.poll_interval = poll_interval
        self.work_count = 0
        self.ollama_available = True

        print(f"🤖 AI Agent initialized")
        print(f"   Server: {self.base_url}")
        print(f"   Ollama: {self.ollama_url}")
        print(f"   Model: {self.model}")
        print(f"   Actor ID: {self.actor_id}")
        if self.role_id:
            print(f"   Role ID: {self.role_id}")
        print()

        # Check Ollama availability
        self._check_ollama()

    def _check_ollama(self) -> None:
        """Check if Ollama is available and the model is accessible"""
        try:
            # Try to reach the Ollama API
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)

            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Check if our model is available
                model_available = any(self.model in name for name in model_names)

                if model_available:
                    print(f"✅ Ollama is running and model '{self.model}' is available")
                    self.ollama_available = True
                else:
                    print(f"⚠️  Ollama is running but model '{self.model}' not found")
                    print(f"   Available models: {', '.join(model_names)}")
                    print(f"   To download: ollama pull {self.model}")
                    self.ollama_available = False
            else:
                print(f"⚠️  Ollama API returned status {response.status_code}")
                self.ollama_available = False

        except requests.exceptions.ConnectionError:
            print(f"⚠️  Cannot connect to Ollama at {self.ollama_url}")
            print("   Make sure Ollama is running: https://ollama.ai")
            self.ollama_available = False
        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout connecting to Ollama")
            self.ollama_available = False
        except Exception as e:
            print(f"⚠️  Error checking Ollama: {e}")
            self.ollama_available = False

        print()

    def checkout_work(self) -> Optional[Dict[str, Any]]:
        """
        Poll the server for available work in the AI_Analyzer role.

        Returns:
            Dict with uow_id, attributes, and context if work found, None otherwise
        """
        try:
            # Prepare checkout request
            request_data = {
                "actor_id": self.actor_id,
                "role_id": self.role_id,
            }

            # Make POST request to checkout endpoint
            response = requests.post(
                f"{self.base_url}/workflow/checkout",
                json=request_data,
                timeout=10,
            )

            # Handle 204 No Content (no work available)
            if response.status_code == 204:
                return None

            # Handle other non-200 responses
            if response.status_code != 200:
                print(f"❌ Error checking out work: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

            # Parse successful response
            work = response.json()
            return work

        except requests.exceptions.Timeout:
            print("⏱️  Request timeout while checking out work")
            return None
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - is the server running?")
            return None
        except Exception as e:
            print(f"❌ Unexpected error during checkout: {e}")
            return None

    def submit_work(
        self, uow_id: str, result_attributes: Dict[str, Any], reasoning: Optional[str] = None
    ) -> bool:
        """
        Submit completed work back to the server.

        Args:
            uow_id: UUID of the Unit of Work
            result_attributes: Dictionary of results to add to the UOW
            reasoning: Optional explanation of the analysis

        Returns:
            True if submission successful, False otherwise
        """
        try:
            # Prepare submit request
            request_data = {
                "uow_id": uow_id,
                "actor_id": self.actor_id,
                "result_attributes": result_attributes,
                "reasoning": reasoning,
            }

            # Make POST request to submit endpoint
            response = requests.post(
                f"{self.base_url}/workflow/submit",
                json=request_data,
                timeout=10,
            )

            if response.status_code != 200:
                print(f"❌ Error submitting work: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

            result = response.json()
            if result.get("success"):
                return True
            else:
                print(f"❌ Submission failed: {result.get('message', 'Unknown error')}")
                return False

        except requests.exceptions.Timeout:
            print("⏱️  Request timeout while submitting work")
            return False
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - is the server running?")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during submission: {e}")
            return False

    def report_failure(self, uow_id: str, error_code: str, details: str) -> bool:
        """
        Report a failure for a Unit of Work.

        Args:
            uow_id: UUID of the Unit of Work
            error_code: Error code for categorization
            details: Detailed error description

        Returns:
            True if failure reported successfully, False otherwise
        """
        try:
            # Prepare failure report request
            request_data = {
                "uow_id": uow_id,
                "actor_id": self.actor_id,
                "error_code": error_code,
                "details": details,
            }

            # Make POST request to failure endpoint
            response = requests.post(
                f"{self.base_url}/workflow/failure",
                json=request_data,
                timeout=10,
            )

            if response.status_code != 200:
                print(f"❌ Error reporting failure: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

            result = response.json()
            return result.get("success", False)

        except Exception as e:
            print(f"❌ Unexpected error reporting failure: {e}")
            return False

    def call_ollama(self, prompt: str) -> Optional[str]:
        """
        Call Ollama API to generate a response.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Generated response text, or None if error
        """
        if not self.ollama_available:
            print("   ⚠️  Ollama is not available, skipping AI generation")
            return None

        try:
            # Prepare Ollama API request
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Get complete response at once
            }

            # Make POST request to Ollama generate endpoint
            print(f"   🤖 Calling Ollama with model '{self.model}'...")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=120,  # Allow up to 2 minutes for generation
            )

            if response.status_code != 200:
                print(f"   ❌ Ollama API error: {response.status_code}")
                return None

            # Parse response
            result = response.json()
            generated_text = result.get("response", "").strip()

            if not generated_text:
                print("   ⚠️  Ollama returned empty response")
                return None

            return generated_text

        except requests.exceptions.Timeout:
            print("   ⏱️  Ollama request timeout (may be too slow or model not loaded)")
            return None
        except requests.exceptions.ConnectionError:
            print("   ❌ Lost connection to Ollama")
            self.ollama_available = False
            return None
        except Exception as e:
            print(f"   ❌ Unexpected error calling Ollama: {e}")
            return None

    def analyze_text(self, attributes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze text using Ollama to generate a summary.

        Args:
            attributes: UOW attributes containing input_text

        Returns:
            Dictionary with ai_summary and metadata, or None if analysis fails
        """
        # Extract input text
        input_text = attributes.get("input_text", "")

        # Convert to string if needed
        if not isinstance(input_text, str):
            input_text = str(input_text)

        if not input_text.strip():
            print("   ⚠️  Warning: No input_text found or empty")
            return None

        # Build prompt for Ollama
        prompt = f"""Summarize the following text concisely in 2-3 sentences:

{input_text}

Summary:"""

        # Call Ollama
        summary = self.call_ollama(prompt)

        if summary is None:
            return None

        # Build result
        result = {
            "ai_summary": summary,
            "analysis_metadata": {
                "model": self.model,
                "input_length": len(input_text),
                "summary_length": len(summary),
                "analyzed_by": self.actor_id,
            },
        }

        return result

    def process_work(self, work: Dict[str, Any]) -> bool:
        """
        Process a work item: analyze text using AI and submit result.

        Args:
            work: Work dictionary with uow_id, attributes, and context

        Returns:
            True if processing successful, False otherwise
        """
        uow_id = work["uow_id"]
        attributes = work.get("attributes", {})

        print(f"\n🧠 Processing UOW: {uow_id}")

        # Check if input_text is present
        input_text = attributes.get("input_text", "")
        if not input_text:
            print("   ❌ Error: No input_text found in attributes")
            # Report failure
            self.report_failure(
                uow_id=uow_id,
                error_code="MISSING_INPUT",
                details="UOW missing required 'input_text' attribute",
            )
            return False

        # Display input text (truncated)
        if isinstance(input_text, str) and len(input_text) > 100:
            print(f"   Input: {input_text[:100]}...")
        else:
            print(f"   Input: {input_text}")

        # Analyze text
        result = self.analyze_text(attributes)

        if result is None:
            print("   ❌ AI analysis failed")
            # Report failure
            self.report_failure(
                uow_id=uow_id,
                error_code="AI_GENERATION_FAILED",
                details="Ollama failed to generate summary (may be offline or overloaded)",
            )
            return False

        # Display summary
        summary = result["ai_summary"]
        if len(summary) > 150:
            print(f"   ✅ Summary: {summary[:150]}...")
        else:
            print(f"   ✅ Summary: {summary}")

        # Submit the work
        reasoning = f"Generated summary using {self.model} model"

        success = self.submit_work(
            uow_id=uow_id,
            result_attributes=result,
            reasoning=reasoning,
        )

        if success:
            self.work_count += 1
            print(f"   ✅ Work submitted successfully (total processed: {self.work_count})")
            return True
        else:
            print("   ❌ Failed to submit work")
            return False

    def run(self) -> None:
        """
        Main agent loop: poll for work, analyze text with AI, and submit results.
        """
        print("🚀 AI Agent started. Polling for work...")
        print(f"   Press Ctrl+C to stop")
        print()

        if not self.ollama_available:
            print("⚠️  WARNING: Starting without Ollama available")
            print("   The agent will report failures for any work it receives")
            print()

        consecutive_empty_polls = 0

        try:
            while True:
                # Check out work
                work = self.checkout_work()

                if work:
                    # Reset counter on successful checkout
                    consecutive_empty_polls = 0

                    # Process the work
                    self.process_work(work)

                    # Brief pause before next poll
                    time.sleep(0.5)
                else:
                    # No work available
                    consecutive_empty_polls += 1

                    # Show waiting message every 10 empty polls
                    if consecutive_empty_polls % 10 == 1:
                        print(f"⏳ Waiting for work... ({consecutive_empty_polls} empty polls, {self.work_count} processed)")

                    # Wait before polling again
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print(f"\n\n👋 AI Agent stopped by user")
            print(f"   Total work items processed: {self.work_count}")
            sys.exit(0)


def main():
    """Main entry point for the AI Agent"""
    parser = argparse.ArgumentParser(
        description="AI Agent for Chameleon Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python examples/ai_agent.py

  # Connect to a custom server and Ollama instance
  python examples/ai_agent.py --base-url http://192.168.1.100:8000 --ollama-url http://192.168.1.100:11434

  # Use a different model
  python examples/ai_agent.py --model mistral

  # Use specific role and actor IDs
  python examples/ai_agent.py --role-id abc-123 --actor-id xyz-789
        """,
    )

    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the Chameleon Workflow Engine server (default: http://localhost:8000)",
    )

    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Base URL of the Ollama API server (default: http://localhost:11434)",
    )

    parser.add_argument(
        "--role-id",
        type=str,
        required=False,
        help="UUID of the AI_Analyzer role (required for checkout)",
    )

    parser.add_argument(
        "--actor-id",
        type=str,
        required=False,
        help="UUID of the AI actor (auto-generated if not provided)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="llama3",
        help="Ollama model to use for generation (default: llama3)",
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Seconds to wait between polling attempts when no work is available (default: 5)",
    )

    args = parser.parse_args()

    # Validate role_id format if provided
    if args.role_id:
        try:
            uuid.UUID(args.role_id)
        except ValueError:
            print(f"❌ Invalid role_id format: {args.role_id}")
            print("   Role ID must be a valid UUID")
            sys.exit(1)

    # Validate actor_id format if provided
    if args.actor_id:
        try:
            uuid.UUID(args.actor_id)
        except ValueError:
            print(f"❌ Invalid actor_id format: {args.actor_id}")
            print("   Actor ID must be a valid UUID")
            sys.exit(1)

    # Check if role_id is provided (required for checkout)
    if not args.role_id:
        print("⚠️  Warning: --role-id not provided")
        print("   You must provide the AI_Analyzer role UUID for the agent to work")
        print()
        print("   To find the role ID:")
        print("   1. Import the workflow: python tools/workflow_manager.py -l -f tools/mixed_agent_workflow.yaml")
        print("   2. Query the database for the AI_Analyzer role UUID")
        print()
        sys.exit(1)

    # Create and run the agent
    agent = AIAgent(
        base_url=args.base_url,
        ollama_url=args.ollama_url,
        role_id=args.role_id,
        actor_id=args.actor_id,
        model=args.model,
        poll_interval=args.poll_interval,
    )

    agent.run()


if __name__ == "__main__":
    main()
