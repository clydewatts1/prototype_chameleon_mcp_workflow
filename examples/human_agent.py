#!/usr/bin/env python3
"""
Human Agent for Chameleon Workflow Engine

This agent demonstrates human-in-the-loop processing in the Chameleon system.
It polls for work from the "Human_Approver" role, displays UOW attributes to the
console, prompts the user for an approval decision, and submits the result.

Usage:
    python examples/human_agent.py --base-url http://localhost:8000
    python examples/human_agent.py --role-id <UUID> --actor-id <UUID>
"""

import argparse
import sys
import time
import uuid
import requests
from typing import Dict, Any, Optional
import json


class HumanAgent:
    """Human Agent for interactive workflow approval"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        role_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        poll_interval: int = 5,
    ):
        """
        Initialize the Human Agent.

        Args:
            base_url: Base URL of the Chameleon Workflow Engine server
            role_id: UUID of the Human_Approver role (if known)
            actor_id: UUID of the human actor (generated if not provided)
            poll_interval: Seconds to wait between polling attempts
        """
        self.base_url = base_url.rstrip("/")
        self.role_id = role_id
        self.actor_id = actor_id or str(uuid.uuid4())
        self.poll_interval = poll_interval

        print(f"🤖 Human Agent initialized")
        print(f"   Server: {self.base_url}")
        print(f"   Actor ID: {self.actor_id}")
        if self.role_id:
            print(f"   Role ID: {self.role_id}")
        print()

    def checkout_work(self) -> Optional[Dict[str, Any]]:
        """
        Poll the server for available work in the Human_Approver role.

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
            reasoning: Optional explanation of the decision

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
                print("✅ Work submitted successfully")
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

    def display_uow(self, work: Dict[str, Any]) -> None:
        """
        Display UOW details to the console in a human-readable format.

        Args:
            work: Work dictionary containing uow_id, attributes, and context
        """
        print("\n" + "=" * 80)
        print("📋 WORK ITEM RECEIVED")
        print("=" * 80)

        print(f"\n🆔 UOW ID: {work['uow_id']}")

        # Display attributes
        print("\n📊 UOW Attributes:")
        attributes = work.get("attributes", {})
        if attributes:
            for key, value in attributes.items():
                # Format the value nicely
                if isinstance(value, dict):
                    value_str = json.dumps(value, indent=2)
                elif isinstance(value, (list, tuple)):
                    value_str = json.dumps(value, indent=2)
                else:
                    value_str = str(value)

                # Highlight important fields
                if key in ["ai_summary", "auto_score", "input_text"]:
                    print(f"   🔸 {key}: {value_str}")
                else:
                    print(f"      {key}: {value_str}")
        else:
            print("   (No attributes)")

        # Display context
        print("\n📚 Context:")
        context = work.get("context", {})
        if context:
            for key, value in context.items():
                print(f"      {key}: {value}")
        else:
            print("   (No context)")

        print("\n" + "=" * 80)

    def prompt_approval(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prompt the user for an approval decision.

        Args:
            work: Work dictionary with UOW details

        Returns:
            Dictionary with approval_status and optional reasoning
        """
        while True:
            print("\n❓ Decision: Approve this work? (y/n/q): ", end="", flush=True)
            response = input().strip().lower()

            if response == "q":
                print("\n👋 Quitting...")
                sys.exit(0)
            elif response in ["y", "yes"]:
                # Get optional reasoning
                print("💭 Reasoning (optional, press Enter to skip): ", end="", flush=True)
                reasoning = input().strip()

                return {
                    "approval_status": "APPROVED",
                    "approved_by": self.actor_id,
                    "approval_reasoning": reasoning or "Approved by human reviewer",
                }
            elif response in ["n", "no"]:
                # Get required reasoning for rejection
                print("💭 Rejection reason (required): ", end="", flush=True)
                reasoning = input().strip()

                while not reasoning:
                    print("⚠️  Rejection reason is required. Please provide a reason: ", end="", flush=True)
                    reasoning = input().strip()

                return {
                    "approval_status": "REJECTED",
                    "rejected_by": self.actor_id,
                    "rejection_reasoning": reasoning,
                }
            else:
                print("⚠️  Invalid input. Please enter 'y' for yes, 'n' for no, or 'q' to quit.")

    def run(self) -> None:
        """
        Main agent loop: poll for work, prompt user, and submit results.
        """
        print("🚀 Human Agent started. Polling for work...")
        print(f"   Press Ctrl+C to stop")
        print()

        consecutive_empty_polls = 0

        try:
            while True:
                # Check out work
                work = self.checkout_work()

                if work:
                    # Reset counter on successful checkout
                    consecutive_empty_polls = 0

                    # Display the work
                    self.display_uow(work)

                    # Prompt for approval
                    decision = self.prompt_approval(work)

                    # Extract reasoning if present
                    reasoning = decision.get("approval_reasoning") or decision.get("rejection_reasoning")

                    # Submit the work
                    success = self.submit_work(
                        uow_id=work["uow_id"],
                        result_attributes=decision,
                        reasoning=reasoning,
                    )

                    if success:
                        print(f"\n✅ Decision recorded: {decision['approval_status']}")
                    else:
                        print("\n❌ Failed to submit decision. The work may be reassigned.")

                    # Brief pause before next poll
                    time.sleep(1)
                else:
                    # No work available
                    consecutive_empty_polls += 1

                    # Show waiting message every 5 empty polls
                    if consecutive_empty_polls % 5 == 1:
                        print(f"⏳ Waiting for work... ({consecutive_empty_polls} empty polls)")

                    # Wait before polling again
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Human Agent stopped by user")
            sys.exit(0)


def main():
    """Main entry point for the Human Agent"""
    parser = argparse.ArgumentParser(
        description="Human Agent for Chameleon Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python examples/human_agent.py

  # Connect to a custom server
  python examples/human_agent.py --base-url http://192.168.1.100:8000

  # Use specific role and actor IDs
  python examples/human_agent.py --role-id abc-123 --actor-id xyz-789

  # Adjust polling interval
  python examples/human_agent.py --poll-interval 10
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
        help="UUID of the Human_Approver role (required for checkout)",
    )

    parser.add_argument(
        "--actor-id",
        type=str,
        required=False,
        help="UUID of the human actor (auto-generated if not provided)",
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
        print("   You must provide the Human_Approver role UUID for the agent to work")
        print()
        print("   To find the role ID:")
        print("   1. Import the workflow: python tools/workflow_manager.py -l -f tools/mixed_agent_workflow.yaml")
        print("   2. Query the database for the Human_Approver role UUID")
        print()
        sys.exit(1)

    # Create and run the agent
    agent = HumanAgent(
        base_url=args.base_url,
        role_id=args.role_id,
        actor_id=args.actor_id,
        poll_interval=args.poll_interval,
    )

    agent.run()


if __name__ == "__main__":
    main()
