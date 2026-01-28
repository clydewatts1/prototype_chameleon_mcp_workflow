#!/usr/bin/env python3
"""
Auto Agent for Chameleon Workflow Engine

This agent demonstrates automated deterministic processing in the Chameleon system.
It polls for work from the "Auto_Calculator" role, performs a deterministic calculation
based on the AI summary, and submits the result.

LOGIC-BLIND ARCHITECTURE
========================
Per Article V.2 & IX.1 (Workflow Constitution), this agent implements a Logic-Blind
BETA role pattern: it emits only computation results without internal routing logic.
Routing decisions are made by the Guardian layer via interaction_policy DSL evaluation.

BETA Attributes Emitted (Calculated Score from Analysis):
  - auto_score: Calculated score based on summary length and keywords
  - score_metadata: Metadata about the calculation (base, bonus, penalty values)

Routing Decision: Made by Guardian's interaction_policy on OUTBOUND components,
  NOT by this agent. The agent trusts the Guardian to route based on BETA attributes
  (e.g., route to High_Priority if auto_score > 800, else Standard_Queue).

Usage:
    python examples/auto_agent.py --base-url http://localhost:8000
    python examples/auto_agent.py --role-id <UUID> --actor-id <UUID>
"""

import argparse
import sys
import time
import uuid
import requests
from typing import Dict, Any, Optional


class AutoAgent:
    """Automated Agent for deterministic calculations"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        role_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        poll_interval: int = 5,
        processing_delay: int = 1,
    ):
        """
        Initialize the Auto Agent.

        Args:
            base_url: Base URL of the Chameleon Workflow Engine server
            role_id: UUID of the Auto_Calculator role (if known)
            actor_id: UUID of the auto actor (generated if not provided)
            poll_interval: Seconds to wait between polling attempts
            processing_delay: Seconds to simulate processing work
        """
        self.base_url = base_url.rstrip("/")
        self.role_id = role_id
        self.actor_id = actor_id or str(uuid.uuid4())
        self.poll_interval = poll_interval
        self.processing_delay = processing_delay
        self.work_count = 0

        print("🤖 Auto Agent initialized")
        print(f"   Server: {self.base_url}")
        print(f"   Actor ID: {self.actor_id}")
        if self.role_id:
            print(f"   Role ID: {self.role_id}")
        print(f"   Processing delay: {self.processing_delay}s")
        print()

    def checkout_work(self) -> Optional[Dict[str, Any]]:
        """
        Poll the server for available work in the Auto_Calculator role.

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
            reasoning: Optional explanation of the calculation

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

    def calculate_score(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform deterministic calculation based on UOW attributes.

        This is a simple scoring algorithm:
        - Base score: length of AI summary * 10
        - Bonus: +50 if summary contains keywords like "important", "critical", "urgent"
        - Penalty: -25 if summary is very short (< 50 chars)

        Args:
            attributes: UOW attributes containing ai_summary

        Returns:
            Dictionary with calculated score and metadata
        """
        # Extract AI summary
        ai_summary = attributes.get("ai_summary", "")

        # Convert to string if it's not already
        if not isinstance(ai_summary, str):
            ai_summary = str(ai_summary)

        # Calculate base score (length * 10)
        base_score = len(ai_summary) * 10

        # Apply bonuses and penalties
        bonus = 0
        penalty = 0

        # Bonus for important keywords
        important_keywords = ["important", "critical", "urgent", "priority", "essential"]
        keyword_count = sum(
            1 for keyword in important_keywords if keyword.lower() in ai_summary.lower()
        )
        bonus = keyword_count * 50

        # Penalty for very short summaries
        if len(ai_summary) < 50:
            penalty = 25

        # Calculate final score
        final_score = max(0, base_score + bonus - penalty)

        # Build result
        result = {
            "auto_score": final_score,
            "calculation_metadata": {
                "base_score": base_score,
                "bonus": bonus,
                "penalty": penalty,
                "summary_length": len(ai_summary),
                "keywords_found": keyword_count,
            },
            "calculated_by": self.actor_id,
        }

        return result

    def process_work(self, work: Dict[str, Any]) -> bool:
        """
        Process a work item: calculate score and submit result.

        Args:
            work: Work dictionary with uow_id, attributes, and context

        Returns:
            True if processing successful, False otherwise
        """
        uow_id = work["uow_id"]
        attributes = work.get("attributes", {})

        print(f"\n📊 Processing UOW: {uow_id}")

        # Check if ai_summary is present
        if "ai_summary" not in attributes:
            print("   ⚠️  Warning: No ai_summary found in attributes")
            print("   Using empty string for calculation")

        # Display AI summary
        ai_summary = attributes.get("ai_summary", "")
        if isinstance(ai_summary, str) and len(ai_summary) > 100:
            print(f"   AI Summary: {ai_summary[:100]}...")
        else:
            print(f"   AI Summary: {ai_summary}")

        # Simulate processing time
        if self.processing_delay > 0:
            print(f"   ⏳ Calculating score (simulating {self.processing_delay}s work)...")
            time.sleep(self.processing_delay)

        # Calculate score
        result = self.calculate_score(attributes)

        print(f"   ✅ Score calculated: {result['auto_score']}")
        print(f"      Base: {result['calculation_metadata']['base_score']}")
        print(f"      Bonus: +{result['calculation_metadata']['bonus']}")
        print(f"      Penalty: -{result['calculation_metadata']['penalty']}")

        # Submit the work
        reasoning = (
            f"Calculated score based on summary length ({result['calculation_metadata']['summary_length']} chars) "
            f"with {result['calculation_metadata']['keywords_found']} important keywords"
        )

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
        Main agent loop: poll for work, calculate scores, and submit results.
        """
        print("🚀 Auto Agent started. Polling for work...")
        print("   Press Ctrl+C to stop")
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
                        print(
                            f"⏳ Waiting for work... ({consecutive_empty_polls} empty polls, {self.work_count} processed)"
                        )

                    # Wait before polling again
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Auto Agent stopped by user")
            print(f"   Total work items processed: {self.work_count}")
            sys.exit(0)


def main():
    """Main entry point for the Auto Agent"""
    parser = argparse.ArgumentParser(
        description="Auto Agent for Chameleon Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python examples/auto_agent.py

  # Connect to a custom server
  python examples/auto_agent.py --base-url http://192.168.1.100:8000

  # Use specific role and actor IDs
  python examples/auto_agent.py --role-id abc-123 --actor-id xyz-789

  # Adjust polling interval and processing delay
  python examples/auto_agent.py --poll-interval 10 --processing-delay 2
        """,
    )

    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the Chameleon Workflow Engine server (default: http://localhost:8000)",
    )

    parser.add_argument(
        "--role-id",
        type=str,
        required=False,
        help="UUID of the Auto_Calculator role (required for checkout)",
    )

    parser.add_argument(
        "--actor-id",
        type=str,
        required=False,
        help="UUID of the auto actor (auto-generated if not provided)",
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Seconds to wait between polling attempts when no work is available (default: 5)",
    )

    parser.add_argument(
        "--processing-delay",
        type=int,
        default=1,
        help="Seconds to simulate processing work (default: 1)",
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
        print("   You must provide the Auto_Calculator role UUID for the agent to work")
        print()
        print("   To find the role ID:")
        print(
            "   1. Import the workflow: python tools/workflow_manager.py -i -f tools/mixed_agent_workflow.yaml"
        )
        print("   2. Query the database for the Auto_Calculator role UUID")
        print()
        sys.exit(1)

    # Create and run the agent
    agent = AutoAgent(
        base_url=args.base_url,
        role_id=args.role_id,
        actor_id=args.actor_id,
        poll_interval=args.poll_interval,
        processing_delay=args.processing_delay,
    )

    agent.run()


if __name__ == "__main__":
    main()
