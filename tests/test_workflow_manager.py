"""
Tests for the workflow_manager CLI tool.

This test suite validates the Export, Import, and DOT graph generation
features of the workflow manager.
"""

import os
import tempfile
import unittest
from pathlib import Path
import yaml

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.manager import DatabaseManager
from database.models_template import (
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    Template_Guardians,
)
from tools.workflow_manager import WorkflowManager


class TestWorkflowManager(unittest.TestCase):
    """Test cases for WorkflowManager."""

    @classmethod
    def setUpClass(cls):
        """Set up test database with sample data."""
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        cls.db_url = f"sqlite:///{cls.temp_db.name}"

        # Initialize database
        cls.db_manager = DatabaseManager(template_url=cls.db_url)
        cls.db_manager.create_template_schema()

        # Create sample workflow that meets Constitutional requirements
        with cls.db_manager.get_template_session() as session:
            # Create workflow
            workflow = Template_Workflows(
                name="TestWorkflow",
                description="A test workflow for validation",
                version=1,
                ai_context={"goal": "Test workflow operations"},
            )
            session.add(workflow)
            session.flush()

            # Create roles - must include ALPHA, OMEGA, EPSILON, TAU per Constitution
            role_alpha = Template_Roles(
                workflow_id=workflow.workflow_id,
                name="AlphaRole",
                description="Origin role",
                role_type="ALPHA",
                ai_context={"instructions": "Start the process"},
            )
            role_beta = Template_Roles(
                workflow_id=workflow.workflow_id,
                name="BetaRole",
                description="Processing role",
                role_type="BETA",
                strategy="HOMOGENEOUS",
            )
            role_omega = Template_Roles(
                workflow_id=workflow.workflow_id,
                name="OmegaRole",
                description="Terminal role",
                role_type="OMEGA",
            )
            role_epsilon = Template_Roles(
                workflow_id=workflow.workflow_id,
                name="EpsilonRole",
                description="Error handler role",
                role_type="EPSILON",
            )
            role_tau = Template_Roles(
                workflow_id=workflow.workflow_id,
                name="TauRole",
                description="Timeout handler role",
                role_type="TAU",
            )
            session.add_all([role_alpha, role_beta, role_omega, role_epsilon, role_tau])
            session.flush()

            # Create interactions
            interaction_1 = Template_Interactions(
                workflow_id=workflow.workflow_id,
                name="Queue1",
                description="First queue",
            )
            interaction_2 = Template_Interactions(
                workflow_id=workflow.workflow_id,
                name="Queue2",
                description="Second queue",
            )
            interaction_3 = Template_Interactions(
                workflow_id=workflow.workflow_id,
                name="Queue3",
                description="Third queue",
            )
            session.add_all([interaction_1, interaction_2, interaction_3])
            session.flush()

            # Create components to satisfy Constitutional requirements
            # R10: ALPHA must have OUTBOUND
            component_1 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_alpha.role_id,
                interaction_id=interaction_1.interaction_id,
                name="Component1",
                description="First component",
                direction="OUTBOUND",
            )
            # R7: Queue1 needs consumer
            component_2 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_beta.role_id,
                interaction_id=interaction_1.interaction_id,
                name="Component2",
                description="Second component",
                direction="INBOUND",
            )
            # R7: Queue2 needs producer
            component_3 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_beta.role_id,
                interaction_id=interaction_2.interaction_id,
                name="Component3",
                description="Third component",
                direction="OUTBOUND",
            )
            # R10: OMEGA must have INBOUND
            component_4 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_omega.role_id,
                interaction_id=interaction_2.interaction_id,
                name="Component4",
                description="Fourth component",
                direction="INBOUND",
            )
            # R8: EPSILON INBOUND must have guardian
            component_5 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_epsilon.role_id,
                interaction_id=interaction_3.interaction_id,
                name="Component5",
                description="Fifth component - Error input",
                direction="INBOUND",
            )
            # R7: Queue3 needs producer
            component_6 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_tau.role_id,
                interaction_id=interaction_3.interaction_id,
                name="Component6",
                description="Sixth component - Timeout output",
                direction="OUTBOUND",
            )
            session.add_all([component_1, component_2, component_3, component_4, component_5, component_6])
            session.flush()

            # Create guardians
            # R9: OMEGA INBOUND must have CERBERUS guardian
            guardian_1 = Template_Guardians(
                workflow_id=workflow.workflow_id,
                component_id=component_4.component_id,
                name="Guardian1",
                description="Cerberus guard for Omega",
                type="CERBERUS",
                config={"sync_strategy": "all_complete"},
            )
            # R8: EPSILON INBOUND must have guardian
            guardian_2 = Template_Guardians(
                workflow_id=workflow.workflow_id,
                component_id=component_5.component_id,
                name="Guardian2",
                description="Guard for Epsilon",
                type="PASS_THRU",
                config={"validation": "basic"},
            )
            session.add_all([guardian_1, guardian_2])

    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        cls.db_manager.close()
        import time
        time.sleep(0.1)  # Pause to release file locks on Windows
        try:
            os.unlink(cls.temp_db.name)
        except PermissionError:
            pass  # File may be locked on Windows

    def test_export_yaml(self):
        """Test YAML export functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkflowManager(db_url=self.db_url)
            output_file = os.path.join(tmpdir, "test_export.yml")

            # Export workflow
            result = manager.export_yaml("TestWorkflow", output_file)

            # Verify file was created
            self.assertTrue(os.path.exists(result))

            # Load and verify YAML content
            with open(result, "r") as f:
                data = yaml.safe_load(f)

            self.assertIn("workflow", data)
            self.assertEqual(data["workflow"]["name"], "TestWorkflow")
            self.assertIn("roles", data)
            self.assertEqual(len(data["roles"]), 5)  # ALPHA, BETA, OMEGA, EPSILON, TAU
            self.assertIn("interactions", data)
            self.assertEqual(len(data["interactions"]), 3)  # Queue1, Queue2, Queue3
            self.assertIn("components", data)
            self.assertEqual(len(data["components"]), 6)  # 6 components
            self.assertIn("guardians", data)
            self.assertEqual(len(data["guardians"]), 2)  # 2 guardians

            # Verify name-based references
            self.assertEqual(data["components"][0]["role_name"], "AlphaRole")
            self.assertEqual(data["components"][0]["interaction_name"], "Queue1")

            manager.close()

    def test_import_yaml(self):
        """Test YAML import functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkflowManager(db_url=self.db_url)

            # First export the workflow
            export_file = os.path.join(tmpdir, "test_export.yml")
            manager.export_yaml("TestWorkflow", export_file)

            # Modify the YAML to create a new workflow
            with open(export_file, "r") as f:
                data = yaml.safe_load(f)

            data["workflow"]["name"] = "ImportedWorkflow"
            data["workflow"]["description"] = "A modified imported workflow"

            import_file = os.path.join(tmpdir, "test_import.yml")
            with open(import_file, "w") as f:
                yaml.dump(data, f)

            # Import the modified workflow
            result = manager.import_yaml(import_file)
            self.assertEqual(result, "ImportedWorkflow")

            # Verify the workflow was created
            with self.db_manager.get_template_session() as session:
                workflow = (
                    session.query(Template_Workflows)
                    .filter(Template_Workflows.name == "ImportedWorkflow")
                    .first()
                )
                self.assertIsNotNone(workflow)
                self.assertEqual(workflow.description, "A modified imported workflow")

                # Verify relationships were created
                self.assertEqual(len(workflow.roles), 5)  # ALPHA, BETA, OMEGA, EPSILON, TAU
                self.assertEqual(len(workflow.interactions), 3)  # Queue1, Queue2, Queue3
                self.assertEqual(len(workflow.components), 6)  # 6 components
                self.assertEqual(len(workflow.guardians), 2)  # 2 guardians

            manager.close()

    def test_reimport_yaml_cascade_delete(self):
        """Test that reimporting a workflow deletes the old one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkflowManager(db_url=self.db_url)

            # Export existing workflow
            export_file = os.path.join(tmpdir, "test_export.yml")
            manager.export_yaml("TestWorkflow", export_file)

            # Get original workflow ID
            with self.db_manager.get_template_session() as session:
                original_workflow = (
                    session.query(Template_Workflows)
                    .filter(Template_Workflows.name == "TestWorkflow")
                    .first()
                )
                original_id = original_workflow.workflow_id

            # Re-import the same workflow
            manager.import_yaml(export_file)

            # Verify a new workflow was created with a different ID
            with self.db_manager.get_template_session() as session:
                new_workflow = (
                    session.query(Template_Workflows)
                    .filter(Template_Workflows.name == "TestWorkflow")
                    .first()
                )
                self.assertIsNotNone(new_workflow)
                self.assertNotEqual(new_workflow.workflow_id, original_id)

            manager.close()

    def test_export_dot(self):
        """Test DOT graph export functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkflowManager(db_url=self.db_url)
            output_file = os.path.join(tmpdir, "test_graph.dot")

            # Export DOT graph
            result = manager.export_dot("TestWorkflow", output_file)

            # Verify file was created
            self.assertTrue(os.path.exists(result))

            # Read and verify DOT content
            with open(result, "r") as f:
                content = f.read()

            # Check for key elements
            self.assertIn('digraph "TestWorkflow"', content)
            self.assertIn("role_AlphaRole", content)
            self.assertIn("role_BetaRole", content)
            self.assertIn("interaction_Queue1", content)
            self.assertIn("interaction_Queue2", content)
            self.assertIn("guardian_Guardian1", content)

            # Check for node shapes
            self.assertIn("shape=circle", content)
            self.assertIn("shape=hexagon", content)
            self.assertIn("shape=doubleoctagon", content)

            # Check for edges
            self.assertIn("->", content)

            manager.close()

    def test_workflow_not_found(self):
        """Test error handling for non-existent workflow."""
        manager = WorkflowManager(db_url=self.db_url)

        with self.assertRaises(ValueError) as context:
            manager.export_yaml("NonExistentWorkflow")

        self.assertIn("not found", str(context.exception))
        manager.close()

    def test_invalid_yaml_import(self):
        """Test error handling for invalid YAML structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkflowManager(db_url=self.db_url)

            # Create invalid YAML file
            invalid_file = os.path.join(tmpdir, "invalid.yml")
            with open(invalid_file, "w") as f:
                yaml.dump({"invalid": "structure"}, f)

            with self.assertRaises(ValueError) as context:
                manager.import_yaml(invalid_file)

            self.assertIn("missing 'workflow' section", str(context.exception))
            manager.close()


if __name__ == "__main__":
    unittest.main()
