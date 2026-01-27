#!/usr/bin/env python3
"""
CLI utility for managing Workflow Templates (Tier 1 Meta-Store).

This tool handles:
- Exporting workflow blueprints to YAML
- Importing/Loading workflow blueprints from YAML
- Generating visual DOT graphs of workflow topology

Usage:
    python tools/workflow_manager.py -w "MyWorkflow" -e           # Export YAML
    python tools/workflow_manager.py -i -f my_flow.yml           # Import YAML
    -                          # List all workflows
    python tools/workflow_manager.py -w "MyWorkflow" --graph     # Export DOT graph
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.manager import DatabaseManager
from database.models_template import (
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    Template_Guardians,
)
from common.config import TEMPLATE_DB_URL


class WorkflowManager:
    """Manages workflow template export, import, and visualization."""

    def __init__(self, db_url: str = "sqlite:///chameleon_workflow.db"):
        """
        Initialize the workflow manager.

        Args:
            db_url: Database connection URL for template database.
        """
        self.manager = DatabaseManager(template_url=db_url)
        self.manager.create_template_schema()

    def export_yaml(self, workflow_name: str, filename: Optional[str] = None) -> str:
        """
        Export a workflow template to YAML format.

        Args:
            workflow_name: Name of the workflow to export.
            filename: Optional output filename. Defaults to workflow_<name>.yml

        Returns:
            Path to the exported file.

        Raises:
            ValueError: If workflow not found.
        """
        with self.manager.get_template_session() as session:
            # Look up the workflow by name
            workflow = (
                session.query(Template_Workflows)
                .filter(Template_Workflows.name == workflow_name)
                .first()
            )

            if not workflow:
                raise ValueError(f"Workflow '{workflow_name}' not found in database.")

            # Build the YAML structure with name-based keys
            yaml_data = {
                "workflow": {
                    "name": workflow.name,
                    "description": workflow.description,
                    "version": workflow.version,
                    "ai_context": workflow.ai_context,
                    "schema_json": workflow.schema_json,
                }
            }

            # Fetch and serialize Roles
            roles_list = []
            for role in workflow.roles:
                role_data = {
                    "name": role.name,
                    "description": role.description,
                    "role_type": role.role_type,
                    "strategy": role.strategy,
                    "ai_context": role.ai_context,
                }
                # Handle child workflow reference
                if role.child_workflow:
                    role_data["child_workflow_name"] = role.child_workflow.name
                roles_list.append(role_data)

            if roles_list:
                yaml_data["roles"] = roles_list

            # Fetch and serialize Interactions
            interactions_list = []
            for interaction in workflow.interactions:
                interaction_data = {
                    "name": interaction.name,
                    "description": interaction.description,
                    "ai_context": interaction.ai_context,
                }
                interactions_list.append(interaction_data)

            if interactions_list:
                yaml_data["interactions"] = interactions_list

            # Fetch and serialize Components with name-based references
            components_list = []
            for component in workflow.components:
                component_data = {
                    "name": component.name,
                    "description": component.description,
                    "role_name": component.role.name,
                    "interaction_name": component.interaction.name,
                    "direction": component.direction,
                    "ai_context": component.ai_context,
                }
                components_list.append(component_data)

            if components_list:
                yaml_data["components"] = components_list

            # Fetch and serialize Guardians with component name references
            guardians_list = []
            for guardian in workflow.guardians:
                guardian_data = {
                    "name": guardian.name,
                    "description": guardian.description,
                    "component_name": guardian.component.name,
                    "type": guardian.type,
                    "config": guardian.config,
                    "ai_context": guardian.ai_context,
                }
                guardians_list.append(guardian_data)

            if guardians_list:
                yaml_data["guardians"] = guardians_list

            # Determine output filename
            if not filename:
                filename = f"workflow_{workflow_name}.yml"

            # Write YAML file
            output_path = Path(filename)
            with open(output_path, "w") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

            return str(output_path.absolute())

    def import_yaml(self, filename: str) -> str:
        """
        Import a workflow template from YAML format.

        This will delete any existing workflow with the same name and create
        a fresh version from the YAML file.

        Args:
            filename: Path to the YAML file to import.

        Returns:
            Name of the imported workflow.

        Raises:
            FileNotFoundError: If the YAML file doesn't exist.
            ValueError: If the YAML structure is invalid.
        """
        yaml_path = Path(filename)
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file '{filename}' not found.")

        # Read and parse YAML
        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        if not yaml_data or "workflow" not in yaml_data:
            raise ValueError("Invalid YAML structure: missing 'workflow' section.")

        workflow_data = yaml_data["workflow"]
        workflow_name = workflow_data.get("name")

        if not workflow_name:
            raise ValueError("Invalid YAML structure: workflow must have a 'name'.")

        with self.manager.get_template_session() as session:
            # Check if workflow exists and delete it (cascade delete)
            existing_workflow = (
                session.query(Template_Workflows)
                .filter(Template_Workflows.name == workflow_name)
                .first()
            )

            if existing_workflow:
                session.delete(existing_workflow)
                session.flush()  # Ensure cascade deletes happen

            # Create new workflow
            new_workflow = Template_Workflows(
                name=workflow_data["name"],
                description=workflow_data.get("description"),
                version=workflow_data.get("version", 1),
                ai_context=workflow_data.get("ai_context"),
                schema_json=workflow_data.get("schema_json"),
            )
            session.add(new_workflow)
            session.flush()  # Get the workflow_id

            # Maps to track name -> entity for resolution
            role_map: Dict[str, Template_Roles] = {}
            interaction_map: Dict[str, Template_Interactions] = {}
            component_map: Dict[str, Template_Components] = {}

            # Create Roles
            roles_data = yaml_data.get("roles", [])
            for role_data in roles_data:
                new_role = Template_Roles(
                    workflow_id=new_workflow.workflow_id,
                    name=role_data["name"],
                    description=role_data.get("description"),
                    role_type=role_data["role_type"],
                    strategy=role_data.get("strategy"),
                    ai_context=role_data.get("ai_context"),
                    # child_workflow_id will be resolved in a second pass
                )
                session.add(new_role)
                role_map[new_role.name] = new_role

            # Create Interactions
            interactions_data = yaml_data.get("interactions", [])
            for interaction_data in interactions_data:
                new_interaction = Template_Interactions(
                    workflow_id=new_workflow.workflow_id,
                    name=interaction_data["name"],
                    description=interaction_data.get("description"),
                    ai_context=interaction_data.get("ai_context"),
                )
                session.add(new_interaction)
                interaction_map[new_interaction.name] = new_interaction

            session.flush()  # Ensure all roles and interactions have IDs

            # Create Components (with name-based resolution)
            components_data = yaml_data.get("components", [])
            for component_data in components_data:
                role_name = component_data.get("role_name")
                interaction_name = component_data.get("interaction_name")

                if role_name not in role_map:
                    raise ValueError(
                        f"Component '{component_data['name']}' references unknown role '{role_name}'."
                    )
                if interaction_name not in interaction_map:
                    raise ValueError(
                        f"Component '{component_data['name']}' references unknown interaction '{interaction_name}'."
                    )

                new_component = Template_Components(
                    workflow_id=new_workflow.workflow_id,
                    role_id=role_map[role_name].role_id,
                    interaction_id=interaction_map[interaction_name].interaction_id,
                    name=component_data["name"],
                    description=component_data.get("description"),
                    direction=component_data["direction"],
                    ai_context=component_data.get("ai_context"),
                )
                session.add(new_component)
                component_map[new_component.name] = new_component

            session.flush()  # Ensure all components have IDs

            # Create Guardians (with component name resolution)
            guardians_data = yaml_data.get("guardians", [])
            for guardian_data in guardians_data:
                component_name = guardian_data.get("component_name")

                if component_name not in component_map:
                    raise ValueError(
                        f"Guardian '{guardian_data['name']}' references unknown component '{component_name}'."
                    )

                new_guardian = Template_Guardians(
                    workflow_id=new_workflow.workflow_id,
                    component_id=component_map[component_name].component_id,
                    name=guardian_data["name"],
                    description=guardian_data.get("description"),
                    type=guardian_data["type"],
                    config=guardian_data.get("config"),
                    ai_context=guardian_data.get("ai_context"),
                )
                session.add(new_guardian)

            # Second pass: Resolve child_workflow references for Roles
            for role_data in roles_data:
                child_workflow_name = role_data.get("child_workflow_name")
                if child_workflow_name:
                    # Look up the child workflow by name
                    child_workflow = (
                        session.query(Template_Workflows)
                        .filter(Template_Workflows.name == child_workflow_name)
                        .first()
                    )
                    if child_workflow:
                        role_map[role_data["name"]].child_workflow_id = (
                            child_workflow.workflow_id
                        )
                    else:
                        print(
                            f"Warning: Child workflow '{child_workflow_name}' not found for role '{role_data['name']}'"
                        )

            # Validate workflow topology before committing
            session.flush()  # Ensure all entities are available for validation
            self._validate_workflow_topology(session, new_workflow.workflow_id)

            # Session will commit on successful context exit
            return workflow_name

    def _validate_workflow_topology(self, session, workflow_id) -> None:
        """
        Validate workflow topology against Constitutional rules.
        
        This method enforces all structural requirements defined in the
        Workflow Constitution (docs/architecture/Workflow_Constitution.md).
        
        Args:
            session: Active database session with pending workflow entities.
            workflow_id: UUID of the workflow to validate.
            
        Raises:
            ValueError: If any validation rule is violated, with a descriptive
                       message citing the specific Constitutional article.
        """
        # Query all roles for this workflow
        roles = (
            session.query(Template_Roles)
            .filter(Template_Roles.workflow_id == workflow_id)
            .all()
        )
        
        # Build role type mapping
        roles_by_type = {}
        for role in roles:
            if role.role_type not in roles_by_type:
                roles_by_type[role.role_type] = []
            roles_by_type[role.role_type].append(role)
        
        # R1: Workflow must have exactly one ALPHA role
        alpha_count = len(roles_by_type.get("ALPHA", []))
        if alpha_count != 1:
            raise ValueError(
                f"Violation of Article V: Workflow must have exactly one ALPHA role "
                f"(The Origin). Found: {alpha_count}"
            )
        
        # R2: Workflow must have exactly one OMEGA role
        omega_count = len(roles_by_type.get("OMEGA", []))
        if omega_count != 1:
            raise ValueError(
                f"Violation of Article V: Workflow must have exactly one OMEGA role "
                f"(The Terminal). Found: {omega_count}"
            )
        
        # R3: Workflow must have exactly one EPSILON role
        epsilon_count = len(roles_by_type.get("EPSILON", []))
        if epsilon_count != 1:
            raise ValueError(
                f"Violation of Article V & XI.1: Workflow must have exactly one EPSILON role "
                f"(The Physician) for error remediation. Found: {epsilon_count}"
            )
        
        # R4: Workflow must have exactly one TAU role
        tau_count = len(roles_by_type.get("TAU", []))
        if tau_count != 1:
            raise ValueError(
                f"Violation of Article V & XI.2: Workflow must have exactly one TAU role "
                f"(The Chronometer) for timeout management. Found: {tau_count}"
            )
        
        # R5: All BETA roles must have valid strategy
        beta_roles = roles_by_type.get("BETA", [])
        for beta_role in beta_roles:
            if not beta_role.strategy:
                raise ValueError(
                    f"Violation of Article V.2: BETA role '{beta_role.name}' must have a "
                    f"valid strategy (HOMOGENEOUS or HETEROGENEOUS). Found: None"
                )
            if beta_role.strategy not in ("HOMOGENEOUS", "HETEROGENEOUS"):
                raise ValueError(
                    f"Violation of Article V.2: BETA role '{beta_role.name}' must have a "
                    f"valid strategy (HOMOGENEOUS or HETEROGENEOUS). Found: {beta_role.strategy}"
                )
        
        # Query all components for this workflow
        components = (
            session.query(Template_Components)
            .filter(Template_Components.workflow_id == workflow_id)
            .all()
        )
        
        # R6: All components must have valid directionality
        for component in components:
            if component.direction not in ("INBOUND", "OUTBOUND"):
                raise ValueError(
                    f"Violation of Article IV: Component '{component.name}' must have valid "
                    f"direction (INBOUND or OUTBOUND). Found: {component.direction}"
                )
        
        # Build component indices for efficient lookups
        components_by_interaction = {}
        components_by_role = {}
        for component in components:
            # Index by interaction
            if component.interaction_id not in components_by_interaction:
                components_by_interaction[component.interaction_id] = {
                    "INBOUND": [],
                    "OUTBOUND": []
                }
            components_by_interaction[component.interaction_id][component.direction].append(component)
            
            # Index by role
            if component.role_id not in components_by_role:
                components_by_role[component.role_id] = {
                    "INBOUND": [],
                    "OUTBOUND": []
                }
            components_by_role[component.role_id][component.direction].append(component)
        
        # R7: Interaction flow integrity - all interactions must have producers and consumers
        interactions = (
            session.query(Template_Interactions)
            .filter(Template_Interactions.workflow_id == workflow_id)
            .all()
        )
        
        for interaction in interactions:
            interaction_components = components_by_interaction.get(
                interaction.interaction_id,
                {"INBOUND": [], "OUTBOUND": []}
            )
            producer_count = len(interaction_components["OUTBOUND"])
            consumer_count = len(interaction_components["INBOUND"])
            
            if producer_count < 1 or consumer_count < 1:
                raise ValueError(
                    f"Violation of Article IV: Interaction '{interaction.name}' must have at least "
                    f"one producer (OUTBOUND) and one consumer (INBOUND). "
                    f"Found: {producer_count} producer(s), {consumer_count} consumer(s)"
                )
        
        # Query all guardians for this workflow
        guardians = (
            session.query(Template_Guardians)
            .filter(Template_Guardians.workflow_id == workflow_id)
            .all()
        )
        
        # Build guardian index by component_id
        guardians_by_component = {}
        for guardian in guardians:
            if guardian.component_id not in guardians_by_component:
                guardians_by_component[guardian.component_id] = []
            guardians_by_component[guardian.component_id].append(guardian)
        
        # Get special roles for R8, R9, R10
        epsilon_role = roles_by_type.get("EPSILON", [None])[0]
        omega_role = roles_by_type.get("OMEGA", [None])[0]
        alpha_role = roles_by_type.get("ALPHA", [None])[0]
        
        # R8: The Ate Guard - EPSILON INBOUND components must have guardians
        if epsilon_role:
            epsilon_inbound_components = components_by_role.get(
                epsilon_role.role_id, {}
            ).get("INBOUND", [])
            
            for component in epsilon_inbound_components:
                guardian_count = len(guardians_by_component.get(component.component_id, []))
                if guardian_count < 1:
                    raise ValueError(
                        f"Violation of Article XI.1 (The Ate Guard): Component '{component.name}' "
                        f"connects to EPSILON role (INBOUND) and must have an associated Guardian. "
                        f"Found: {guardian_count} guardian(s)"
                    )
        
        # R9: The Cerberus Mandate - OMEGA INBOUND component must have CERBERUS guardian
        if omega_role:
            omega_inbound_components = components_by_role.get(
                omega_role.role_id, {}
            ).get("INBOUND", [])
            
            for component in omega_inbound_components:
                component_guardians = guardians_by_component.get(component.component_id, [])
                if not component_guardians:
                    raise ValueError(
                        f"Violation of Article VI (The Cerberus Mandate): Component '{component.name}' "
                        f"connects to OMEGA role (INBOUND) and must have a CERBERUS guardian. "
                        f"Found: None"
                    )
                
                # Check if any guardian is of type CERBERUS
                has_cerberus = any(g.type == "CERBERUS" for g in component_guardians)
                if not has_cerberus:
                    guardian_types = [g.type for g in component_guardians]
                    raise ValueError(
                        f"Violation of Article VI (The Cerberus Mandate): Component '{component.name}' "
                        f"connects to OMEGA role (INBOUND) and must have a CERBERUS guardian. "
                        f"Found: {', '.join(guardian_types)}"
                    )
        
        # R10: Topology Flow - ALPHA must have OUTBOUND, OMEGA must have INBOUND
        if alpha_role:
            alpha_outbound_count = len(
                components_by_role.get(alpha_role.role_id, {}).get("OUTBOUND", [])
            )
            if alpha_outbound_count < 1:
                raise ValueError(
                    f"Violation of Article V & VII: ALPHA role must have at least one OUTBOUND "
                    f"component. Found: {alpha_outbound_count}"
                )
        
        if omega_role:
            omega_inbound_count = len(
                components_by_role.get(omega_role.role_id, {}).get("INBOUND", [])
            )
            if omega_inbound_count < 1:
                raise ValueError(
                    f"Violation of Article V & VII: OMEGA role must have at least one INBOUND "
                    f"component. Found: {omega_inbound_count}"
                )

    def delete_workflow(self, workflow_name: str) -> bool:
        """
        Delete a workflow template and all its related entities.

        This will cascade delete all roles, interactions, components, and guardians
        associated with the workflow.

        Args:
            workflow_name: Name of the workflow to delete.

        Returns:
            True if workflow was deleted, False if not found.

        Raises:
            Exception: If deletion fails.
        """
        with self.manager.get_template_session() as session:
            # Look up the workflow by name
            workflow = (
                session.query(Template_Workflows)
                .filter(Template_Workflows.name == workflow_name)
                .first()
            )

            if not workflow:
                return False

            # Delete the workflow (cascade will handle related entities)
            session.delete(workflow)
            session.flush()

            # Session will commit on successful context exit
            return True

    def export_dot(self, workflow_name: str, filename: Optional[str] = None) -> str:
        """
        Export a workflow template as a DOT graph file.

        Args:
            workflow_name: Name of the workflow to export.
            filename: Optional output filename. Defaults to workflow_<name>.dot

        Returns:
            Path to the exported file.

        Raises:
            ValueError: If workflow not found.
        """
        with self.manager.get_template_session() as session:
            # Look up the workflow by name
            workflow = (
                session.query(Template_Workflows)
                .filter(Template_Workflows.name == workflow_name)
                .first()
            )

            if not workflow:
                raise ValueError(f"Workflow '{workflow_name}' not found in database.")

            # Start building the DOT file
            dot_lines = [
                f'digraph "{workflow.name}" {{',
                '  label="' + workflow.name.replace('"', '\\"') + '";',
                '  labelloc="t";',
                '  node [fontname="Arial"];',
                '  edge [fontname="Arial"];',
                "",
            ]

            # Add Roles as circular nodes with role-type specific colors and thick borders
            role_colors = {
                "ALPHA": "green",
                "BETA": "blue",
                "OMEGA": "black",
                "EPSILON": "orange",
                "TAU": "purple"
            }
            
            for role in workflow.roles:
                label = role.name.replace('"', '\\"')
                node_id = f'role_{role.name.replace(" ", "_")}'
                color = role_colors.get(role.role_type, "gray")
                dot_lines.append(
                    f'  {node_id} [label="{label}", shape=circle, style=filled, fillcolor=lightgray, color={color}, penwidth=3];'
                )

            # Add Interactions as hexagonal nodes
            for interaction in workflow.interactions:
                label = interaction.name.replace('"', '\\"')
                node_id = f'interaction_{interaction.name.replace(" ", "_")}'
                dot_lines.append(
                    f'  {node_id} [label="{label}", shape=hexagon, style=filled, fillcolor=lightgreen];'
                )

            # Add Guardians as doubleoctagon nodes
            guardian_by_component = {}
            for guardian in workflow.guardians:
                guardian_by_component[guardian.component_id] = guardian
                label = guardian.name.replace('"', '\\"')
                node_id = f'guardian_{guardian.name.replace(" ", "_")}'
                dot_lines.append(
                    f'  {node_id} [label="{label}", shape=doubleoctagon, style=filled, fillcolor=salmon];'
                )

            dot_lines.append("")

            # Add Components as edges
            for component in workflow.components:
                role_id = f'role_{component.role.name.replace(" ", "_")}'
                interaction_id = (
                    f'interaction_{component.interaction.name.replace(" ", "_")}'
                )
                edge_label = component.name.replace('"', '\\"')

                # Check if this component has a guardian
                if component.component_id in guardian_by_component:
                    guardian = guardian_by_component[component.component_id]
                    guardian_id = f'guardian_{guardian.name.replace(" ", "_")}'

                    # Place guardian on the edge: Role -> Guardian -> Interaction
                    if component.direction == "OUTBOUND":
                        # Role -> Guardian -> Interaction
                        dot_lines.append(
                            f'  {role_id} -> {guardian_id} [label="{edge_label}"];'
                        )
                        dot_lines.append(f"  {guardian_id} -> {interaction_id};")
                    else:  # INBOUND
                        # Interaction -> Guardian -> Role
                        dot_lines.append(
                            f'  {interaction_id} -> {guardian_id} [label="{edge_label}"];'
                        )
                        dot_lines.append(f"  {guardian_id} -> {role_id};")
                else:
                    # Direct edge without guardian
                    if component.direction == "OUTBOUND":
                        dot_lines.append(
                            f'  {role_id} -> {interaction_id} [label="{edge_label}"];'
                        )
                    else:  # INBOUND
                        dot_lines.append(
                            f'  {interaction_id} -> {role_id} [label="{edge_label}"];'
                        )

            dot_lines.append("}")

            # Determine output filename
            if not filename:
                filename = f"workflow_{workflow_name}.dot"

            # Write DOT file
            output_path = Path(filename)
            with open(output_path, "w") as f:
                f.write("\n".join(dot_lines))

            return str(output_path.absolute())

    def list_workflows(self) -> list:
        """
        List all workflow templates in the database.

        Returns:
            List of tuples containing (name, version, description) for each workflow.
        """
        with self.manager.get_template_session() as session:
            workflows = session.query(Template_Workflows).all()
            return [
                (wf.name, wf.version, wf.description or "")
                for wf in workflows
            ]

    def close(self):
        """Close database connections."""
        self.manager.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CLI utility for managing Workflow Templates (Tier 1 Meta-Store)."
    )

    parser.add_argument(
        "-w", "--workflow", help="Workflow name for export/graph operations"
    )
    parser.add_argument(
        "-e", "--export", action="store_true", help="Export workflow to YAML"
    )
    parser.add_argument(
        "-i", "--import", dest="import_yaml", action="store_true", help="Import/Load workflow from YAML"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List all workflows in the database"
    )
    parser.add_argument(
        "-d", "--delete", action="store_true", help="Delete a workflow and all its components"
    )
    parser.add_argument("-f", "--file", help="YAML filename for import/export")
    parser.add_argument(
        "--graph", action="store_true", help="Export workflow as DOT graph"
    )
    parser.add_argument(
        "--db",
        default=TEMPLATE_DB_URL,
        help=f"Database URL (default: {TEMPLATE_DB_URL})",
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.export, args.import_yaml, args.graph, args.list, args.delete]):
        parser.error("Must specify one of: -e/--export, -i/--import, -l/--list, -d/--delete, or --graph")

    if args.export and not args.workflow:
        parser.error("-e/--export requires -w/--workflow")

    if args.graph and not args.workflow:
        parser.error("--graph requires -w/--workflow")

    if args.delete and not args.workflow:
        parser.error("-d/--delete requires -w/--workflow")

    if args.import_yaml and not args.file:
        parser.error("-i/--import requires -f/--file")

    # Initialize manager
    try:
        manager = WorkflowManager(db_url=args.db)

        if args.export:
            output_file = manager.export_yaml(args.workflow, args.file)
            print(f"✓ Exported workflow '{args.workflow}' to: {output_file}")

        elif args.import_yaml:
            workflow_name = manager.import_yaml(args.file)
            print(
                f"✓ Imported workflow '{workflow_name}' from: {os.path.abspath(args.file)}"
            )

        elif args.list:
            workflows = manager.list_workflows()
            if workflows:
                print(f"\n{'Name':<30} {'Version':<10} {'Description'}")
                print("-" * 80)
                for name, version, description in workflows:
                    desc_short = (description[:50] + "...") if len(description) > 50 else description
                    print(f"{name:<30} {version:<10} {desc_short}")
                print(f"\nTotal: {len(workflows)} workflow(s)")
            else:
                print("No workflows found in database.")

        elif args.delete:
            deleted = manager.delete_workflow(args.workflow)
            if deleted:
                print(f"✓ Deleted workflow '{args.workflow}' and all its components (roles, interactions, components, guardians)")
            else:
                print(f"✗ Workflow '{args.workflow}' not found")
                sys.exit(1)

        elif args.graph:
            output_file = manager.export_dot(args.workflow, args.file)
            print(f"✓ Exported workflow graph '{args.workflow}' to: {output_file}")

        manager.close()

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
