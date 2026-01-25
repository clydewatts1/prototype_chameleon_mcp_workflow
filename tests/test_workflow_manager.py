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

        # Create sample workflow
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

            # Create roles
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
            session.add_all([role_alpha, role_beta])
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
            session.add_all([interaction_1, interaction_2])
            session.flush()

            # Create components
            component_1 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_alpha.role_id,
                interaction_id=interaction_1.interaction_id,
                name="Component1",
                description="First component",
                direction="OUTBOUND",
            )
            component_2 = Template_Components(
                workflow_id=workflow.workflow_id,
                role_id=role_beta.role_id,
                interaction_id=interaction_1.interaction_id,
                name="Component2",
                description="Second component",
                direction="INBOUND",
            )
            session.add_all([component_1, component_2])
            session.flush()

            # Create guardian
            guardian = Template_Guardians(
                workflow_id=workflow.workflow_id,
                component_id=component_1.component_id,
                name="Guardian1",
                description="Test guardian",
                type="CRITERIA_GATE",
                config={"criteria": "amount > 100"},
            )
            session.add(guardian)

    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        cls.db_manager.close()
        os.unlink(cls.temp_db.name)

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
            self.assertEqual(len(data["roles"]), 2)
            self.assertIn("interactions", data)
            self.assertEqual(len(data["interactions"]), 2)
            self.assertIn("components", data)
            self.assertEqual(len(data["components"]), 2)
            self.assertIn("guardians", data)
            self.assertEqual(len(data["guardians"]), 1)

            # Verify name-based references
            self.assertEqual(data["components"][0]["role_name"], "AlphaRole")
            self.assertEqual(data["components"][0]["interaction_name"], "Queue1")
            self.assertEqual(data["guardians"][0]["component_name"], "Component1")

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
                self.assertEqual(len(workflow.roles), 2)
                self.assertEqual(len(workflow.interactions), 2)
                self.assertEqual(len(workflow.components), 2)
                self.assertEqual(len(workflow.guardians), 1)

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
