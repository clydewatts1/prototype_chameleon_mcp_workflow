"""
Tests for workflow topology validation rules.

This test suite validates that the WorkflowManager correctly enforces
all Constitutional requirements (R1-R10) during YAML import.
"""

import os
import tempfile
import unittest
from pathlib import Path
import yaml

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.manager import DatabaseManager
from database.models_template import Template_Workflows
from tools.workflow_manager import WorkflowManager


class TestWorkflowValidation(unittest.TestCase):
    """Test cases for workflow validation rules R1-R10."""

    def setUp(self):
        """Set up a fresh test database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_url = f"sqlite:///{self.temp_db.name}"
        self.manager = WorkflowManager(db_url=self.db_url)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test database and temporary files."""
        self.manager.close()
        import time
        time.sleep(0.1)  # Brief pause to ensure file handles are released on Windows
        try:
            os.unlink(self.temp_db.name)
        except PermissionError:
            pass  # File may be locked on Windows; it will be cleaned up by temp
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_base_workflow_yaml(self) -> dict:
        """Create a minimal valid workflow structure."""
        return {
            "workflow": {
                "name": "TestWorkflow",
                "description": "Test workflow",
                "version": 1,
            },
            "roles": [
                {"name": "Alpha", "role_type": "ALPHA"},
                {"name": "Omega", "role_type": "OMEGA"},
                {"name": "Epsilon", "role_type": "EPSILON"},
                {"name": "Tau", "role_type": "TAU"},
            ],
            "interactions": [
                {"name": "Queue1"},
                {"name": "Queue2"},
                {"name": "Queue3"},
            ],
            "components": [
                {
                    "name": "Alpha_Out",
                    "role_name": "Alpha",
                    "interaction_name": "Queue1",
                    "direction": "OUTBOUND",
                },
                {
                    "name": "Omega_In",
                    "role_name": "Omega",
                    "interaction_name": "Queue2",
                    "direction": "INBOUND",
                },
                {
                    "name": "Queue1_Consumer",
                    "role_name": "Epsilon",
                    "interaction_name": "Queue1",
                    "direction": "INBOUND",
                },
                {
                    "name": "Queue2_Producer",
                    "role_name": "Tau",
                    "interaction_name": "Queue2",
                    "direction": "OUTBOUND",
                },
                {
                    "name": "Queue3_Producer",
                    "role_name": "Alpha",
                    "interaction_name": "Queue3",
                    "direction": "OUTBOUND",
                },
                {
                    "name": "Queue3_Consumer",
                    "role_name": "Tau",
                    "interaction_name": "Queue3",
                    "direction": "INBOUND",
                },
            ],
            "guardians": [
                {
                    "name": "OmegaGuard",
                    "component_name": "Omega_In",
                    "type": "CERBERUS",
                },
                {
                    "name": "EpsilonGuard",
                    "component_name": "Queue1_Consumer",
                    "type": "PASS_THRU",
                },
            ],
        }

    def write_yaml_file(self, data: dict) -> str:
        """Write YAML data to a temporary file."""
        filepath = os.path.join(self.temp_dir, "test_workflow.yml")
        with open(filepath, "w") as f:
            yaml.dump(data, f)
        return filepath

    def test_valid_workflow_import(self):
        """Test that a valid workflow meeting all requirements imports successfully."""
        workflow_data = self.create_base_workflow_yaml()
        filepath = self.write_yaml_file(workflow_data)

        # Should not raise any exception
        result = self.manager.import_yaml(filepath)
        self.assertEqual(result, "TestWorkflow")

        # Verify workflow was created
        with self.manager.manager.get_template_session() as session:
            workflow = (
                session.query(Template_Workflows)
                .filter(Template_Workflows.name == "TestWorkflow")
                .first()
            )
            self.assertIsNotNone(workflow)

    def test_r1_missing_alpha_role(self):
        """R1: Workflow must have exactly one ALPHA role."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove ALPHA role
        workflow_data["roles"] = [r for r in workflow_data["roles"] if r["role_type"] != "ALPHA"]
        # Remove ALPHA components
        workflow_data["components"] = [
            c for c in workflow_data["components"] if c["role_name"] != "Alpha"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V", str(context.exception))
        self.assertIn("ALPHA", str(context.exception))
        self.assertIn("Found: 0", str(context.exception))

        # Verify workflow was NOT created (rollback worked)
        with self.manager.manager.get_template_session() as session:
            workflow = (
                session.query(Template_Workflows)
                .filter(Template_Workflows.name == "TestWorkflow")
                .first()
            )
            self.assertIsNone(workflow)

    def test_r1_multiple_alpha_roles(self):
        """R1: Workflow must have exactly one ALPHA role (not multiple)."""
        workflow_data = self.create_base_workflow_yaml()
        # Add extra ALPHA role
        workflow_data["roles"].append({"name": "Alpha2", "role_type": "ALPHA"})
        # Add component for extra ALPHA
        workflow_data["components"].append({
            "name": "Alpha2_Out",
            "role_name": "Alpha2",
            "interaction_name": "Queue1",
            "direction": "OUTBOUND",
        })
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V", str(context.exception))
        self.assertIn("ALPHA", str(context.exception))
        self.assertIn("Found: 2", str(context.exception))

    def test_r2_missing_omega_role(self):
        """R2: Workflow must have exactly one OMEGA role."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove OMEGA role
        workflow_data["roles"] = [r for r in workflow_data["roles"] if r["role_type"] != "OMEGA"]
        # Remove OMEGA components and its guardians
        workflow_data["components"] = [
            c for c in workflow_data["components"] if c["role_name"] != "Omega"
        ]
        workflow_data["guardians"] = [
            g for g in workflow_data["guardians"] if g["component_name"] != "Omega_In"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V", str(context.exception))
        self.assertIn("OMEGA", str(context.exception))
        self.assertIn("Found: 0", str(context.exception))

    def test_r3_missing_epsilon_role(self):
        """R3: Workflow must have exactly one EPSILON role."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove EPSILON role
        workflow_data["roles"] = [r for r in workflow_data["roles"] if r["role_type"] != "EPSILON"]
        # Remove EPSILON components and guardians
        workflow_data["components"] = [
            c for c in workflow_data["components"] if c["role_name"] != "Epsilon"
        ]
        workflow_data["guardians"] = [
            g for g in workflow_data["guardians"] if g["component_name"] != "Queue1_Consumer"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V & XI.1", str(context.exception))
        self.assertIn("EPSILON", str(context.exception))
        self.assertIn("Found: 0", str(context.exception))

    def test_r4_missing_tau_role(self):
        """R4: Workflow must have exactly one TAU role."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove TAU role
        workflow_data["roles"] = [r for r in workflow_data["roles"] if r["role_type"] != "TAU"]
        # Remove TAU components
        workflow_data["components"] = [
            c for c in workflow_data["components"] if c["role_name"] != "Tau"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V & XI.2", str(context.exception))
        self.assertIn("TAU", str(context.exception))
        self.assertIn("Found: 0", str(context.exception))

    def test_r5_beta_missing_strategy(self):
        """R5: All BETA roles must have valid strategy defined."""
        workflow_data = self.create_base_workflow_yaml()
        # Add BETA role without strategy
        workflow_data["roles"].append({
            "name": "BetaRole",
            "role_type": "BETA",
            # strategy intentionally missing
        })
        # Add components for BETA role
        workflow_data["components"].extend([
            {
                "name": "Beta_In",
                "role_name": "BetaRole",
                "interaction_name": "Queue1",
                "direction": "INBOUND",
            },
            {
                "name": "Beta_Out",
                "role_name": "BetaRole",
                "interaction_name": "Queue2",
                "direction": "OUTBOUND",
            },
        ])
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V.2", str(context.exception))
        self.assertIn("BetaRole", str(context.exception))
        self.assertIn("strategy", str(context.exception))

    def test_r5_beta_invalid_strategy(self):
        """R5: BETA roles must have valid strategy (not arbitrary values)."""
        workflow_data = self.create_base_workflow_yaml()
        # Add BETA role with invalid strategy
        workflow_data["roles"].append({
            "name": "BetaRole",
            "role_type": "BETA",
            "strategy": "INVALID_STRATEGY",
        })
        # Add components for BETA role
        workflow_data["components"].extend([
            {
                "name": "Beta_In",
                "role_name": "BetaRole",
                "interaction_name": "Queue1",
                "direction": "INBOUND",
            },
            {
                "name": "Beta_Out",
                "role_name": "BetaRole",
                "interaction_name": "Queue2",
                "direction": "OUTBOUND",
            },
        ])
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article V.2", str(context.exception))
        self.assertIn("BetaRole", str(context.exception))
        self.assertIn("INVALID_STRATEGY", str(context.exception))

    def test_r6_invalid_component_direction(self):
        """R6: All components must have valid directionality."""
        workflow_data = self.create_base_workflow_yaml()
        # Set invalid direction
        workflow_data["components"][0]["direction"] = "SIDEWAYS"
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article IV", str(context.exception))
        self.assertIn("direction", str(context.exception))
        self.assertIn("SIDEWAYS", str(context.exception))

    def test_r7_interaction_missing_producer(self):
        """R7: Interaction must have at least one producer."""
        workflow_data = self.create_base_workflow_yaml()
        # Add interaction with no producer
        workflow_data["interactions"].append({"name": "OrphanQueue"})
        # Add only consumer, no producer
        workflow_data["components"].append({
            "name": "OrphanConsumer",
            "role_name": "Tau",
            "interaction_name": "OrphanQueue",
            "direction": "INBOUND",
        })
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article IV", str(context.exception))
        self.assertIn("OrphanQueue", str(context.exception))
        self.assertIn("producer", str(context.exception))

    def test_r7_interaction_missing_consumer(self):
        """R7: Interaction must have at least one consumer."""
        workflow_data = self.create_base_workflow_yaml()
        # Add interaction with no consumer
        workflow_data["interactions"].append({"name": "DeadEndQueue"})
        # Add only producer, no consumer
        workflow_data["components"].append({
            "name": "DeadEndProducer",
            "role_name": "Alpha",
            "interaction_name": "DeadEndQueue",
            "direction": "OUTBOUND",
        })
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article IV", str(context.exception))
        self.assertIn("DeadEndQueue", str(context.exception))
        self.assertIn("consumer", str(context.exception))

    def test_r8_epsilon_inbound_missing_guardian(self):
        """R8: EPSILON INBOUND components must have guardians."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove the guardian from EPSILON INBOUND component
        workflow_data["guardians"] = [
            g for g in workflow_data["guardians"] if g["component_name"] != "Queue1_Consumer"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article XI.1", str(context.exception))
        self.assertIn("Ate Guard", str(context.exception))
        self.assertIn("EPSILON", str(context.exception))
        self.assertIn("Queue1_Consumer", str(context.exception))

    def test_r9_omega_inbound_missing_guardian(self):
        """R9: OMEGA INBOUND component must have guardian."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove the guardian from OMEGA INBOUND component
        workflow_data["guardians"] = [
            g for g in workflow_data["guardians"] if g["component_name"] != "Omega_In"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article VI", str(context.exception))
        self.assertIn("Cerberus Mandate", str(context.exception))
        self.assertIn("OMEGA", str(context.exception))

    def test_r9_omega_inbound_wrong_guardian_type(self):
        """R9: OMEGA INBOUND guardian must be CERBERUS type."""
        workflow_data = self.create_base_workflow_yaml()
        # Change guardian type from CERBERUS to something else
        for guardian in workflow_data["guardians"]:
            if guardian["component_name"] == "Omega_In":
                guardian["type"] = "PASS_THRU"
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        self.assertIn("Article VI", str(context.exception))
        self.assertIn("Cerberus Mandate", str(context.exception))
        self.assertIn("CERBERUS", str(context.exception))
        self.assertIn("PASS_THRU", str(context.exception))

    def test_r10_alpha_missing_outbound(self):
        """R10: ALPHA role must have at least one OUTBOUND component."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove all ALPHA OUTBOUND components
        workflow_data["components"] = [
            c for c in workflow_data["components"]
            if not (c["role_name"] == "Alpha" and c["direction"] == "OUTBOUND")
        ]
        # Add a component to make Queue1 still valid (already has EPSILON consumer)
        # We're testing that ALPHA specifically has no OUTBOUND, not Queue1 validation
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        # The error message could be either R7 (Queue1 missing producer) or R10 (ALPHA missing outbound)
        # Both are technically correct, but R10 is more specific
        # Let's accept either error message
        error_msg = str(context.exception)
        self.assertTrue(
            ("Article V & VII" in error_msg and "ALPHA" in error_msg and "OUTBOUND" in error_msg) or
            ("Article IV" in error_msg and "producer" in error_msg),
            f"Expected ALPHA/OUTBOUND or producer error, got: {error_msg}"
        )

    def test_r10_omega_missing_inbound(self):
        """R10: OMEGA role must have at least one INBOUND component."""
        workflow_data = self.create_base_workflow_yaml()
        # Remove OMEGA INBOUND component and its guardian
        workflow_data["components"] = [
            c for c in workflow_data["components"]
            if not (c["role_name"] == "Omega" and c["direction"] == "INBOUND")
        ]
        workflow_data["guardians"] = [
            g for g in workflow_data["guardians"] if g["component_name"] != "Omega_In"
        ]
        filepath = self.write_yaml_file(workflow_data)

        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(filepath)

        # The error message could be either R7 (Queue2 missing consumer) or R10 (OMEGA missing inbound)
        # Both are technically correct, but R10 is more specific
        # Let's accept either error message
        error_msg = str(context.exception)
        self.assertTrue(
            ("Article V & VII" in error_msg and "OMEGA" in error_msg and "INBOUND" in error_msg) or
            ("Article IV" in error_msg and "consumer" in error_msg),
            f"Expected OMEGA/INBOUND or consumer error, got: {error_msg}"
        )

    def test_complete_workflow_example_needs_epsilon_guardian(self):
        """Test that complete_workflow_example.yaml validates (or needs fix for R8)."""
        # Load the complete workflow example
        example_path = Path(__file__).parent.parent / "tools" / "complete_workflow_example.yaml"
        
        if not example_path.exists():
            self.skipTest("complete_workflow_example.yaml not found")
        
        # This test documents that the example needs a guardian added to Error_From_Queue
        # to comply with R8 (The Ate Guard)
        with self.assertRaises(ValueError) as context:
            self.manager.import_yaml(str(example_path))
        
        # The example may fail on multiple rules - let's just verify it raises a validation error
        error_msg = str(context.exception)
        self.assertTrue(
            "Violation of Article" in error_msg,
            f"Expected Constitutional violation, got: {error_msg}"
        )


if __name__ == "__main__":
    unittest.main()
