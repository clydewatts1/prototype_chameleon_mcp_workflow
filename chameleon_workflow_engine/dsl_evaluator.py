"""
Interaction Policy DSL Evaluator

Implements a simple, safe Domain Specific Language (DSL) for evaluating
interaction_policy conditions in the Guardian system.

DSL Features:
- Python comparison operators: < > <= >= == !=
- Logical operators: and, or, not
- Parentheses for grouping
- Safe namespace: only UOW_Attributes + reserved metadata

Constitutional Reference:
- Article IX.1: Interaction Policy Evaluation
- Workflow_Import_Requirements.md: R11, R12

Authors: Chameleon Workflow Engine
"""

import re
import ast
from typing import Dict, Any, List, Tuple
from loguru import logger


class DSLSyntaxError(ValueError):
    """Raised when DSL condition has invalid syntax."""
    pass


class DSLAttributeError(ValueError):
    """Raised when DSL references unauthorized attribute."""
    pass


class InteractionPolicyDSL:
    """
    DSL evaluator for interaction_policy conditions.
    
    Safe evaluation with restricted namespace and operator whitelist.
    """

    # Permitted comparison and logical operators
    PERMITTED_OPERATORS = {
        # Comparison operators
        ast.Lt,  # <
        ast.Gt,  # >
        ast.LtE,  # <=
        ast.GtE,  # >=
        ast.Eq,  # ==
        ast.NotEq,  # !=
        # Logical operators
        ast.And,
        ast.Or,
        ast.Not,
        # Membership
        ast.In,
        ast.NotIn,
    }

    # Forbidden operators (bitwise, arithmetic, etc.)
    FORBIDDEN_OPERATORS = {
        ast.LShift,  # <<
        ast.RShift,  # >>
        ast.BitOr,  # |
        ast.BitXor,  # ^
        ast.BitAnd,  # &
        ast.Add,  # +
        ast.Sub,  # -
        ast.Mult,  # *
        ast.Div,  # /
        ast.FloorDiv,  # //
        ast.Mod,  # %
        ast.Pow,  # **
        ast.MatMult,  # @
    }

    # Reserved metadata available in evaluation context
    RESERVED_METADATA = {
        "uow_id",
        "child_count",
        "finished_child_count",
        "status",
        "parent_id",
    }

    @staticmethod
    def parse_condition(condition: str) -> ast.Expression:
        """
        Parse a DSL condition into an AST.
        
        Args:
            condition: DSL condition string (e.g., "risk_score > 8 and not is_flagged")
        
        Returns:
            ast.Expression: Parsed AST
        
        Raises:
            DSLSyntaxError: If syntax is invalid
        """
        try:
            tree = ast.parse(condition, mode="eval")
            return tree
        except SyntaxError as e:
            raise DSLSyntaxError(
                f"Invalid DSL syntax: {e.msg} at position {e.offset}"
            ) from e

    @staticmethod
    def _validate_ast_node(node: ast.AST, permitted_attributes: set) -> None:
        """
        Recursively validate AST node structure.
        
        Checks:
        - Only permitted operators used
        - No function calls (security boundary)
        - No attribute access outside permitted set
        
        Args:
            node: AST node to validate
            permitted_attributes: Set of attribute names allowed to reference
        
        Raises:
            DSLSyntaxError: If invalid operator used
            DSLAttributeError: If unauthorized attribute referenced
        """
        if isinstance(node, ast.Compare):
            # Validate comparison operators
            for op in node.ops:
                if type(op) in InteractionPolicyDSL.FORBIDDEN_OPERATORS:
                    raise DSLSyntaxError(
                        f"Unsupported operator: {type(op).__name__}. "
                        f"Only comparison (<, >, <=, >=, ==, !=) and logical (and, or, not) operators allowed."
                    )
                if type(op) not in InteractionPolicyDSL.PERMITTED_OPERATORS:
                    raise DSLSyntaxError(
                        f"Unsupported operator: {type(op).__name__}. "
                        f"Only comparison (<, >, <=, >=, ==, !=) and logical (and, or, not) operators allowed."
                    )
            # Validate left side
            InteractionPolicyDSL._validate_ast_node(node.left, permitted_attributes)
            # Validate comparators
            for comparator in node.comparators:
                InteractionPolicyDSL._validate_ast_node(comparator, permitted_attributes)

        elif isinstance(node, ast.BoolOp):
            # and, or
            for value in node.values:
                InteractionPolicyDSL._validate_ast_node(value, permitted_attributes)

        elif isinstance(node, ast.UnaryOp):
            # not
            if not isinstance(node.op, ast.Not):
                raise DSLSyntaxError(
                    f"Unsupported unary operator: {type(node.op).__name__}. Only 'not' allowed."
                )
            InteractionPolicyDSL._validate_ast_node(node.operand, permitted_attributes)

        elif isinstance(node, ast.Name):
            # Variable reference (attribute name or reserved metadata)
            if node.id not in permitted_attributes:
                raise DSLAttributeError(
                    f"Attribute '{node.id}' not permitted. "
                    f"Use only UOW_Attributes or reserved metadata: {InteractionPolicyDSL.RESERVED_METADATA}"
                )

        elif isinstance(node, (ast.Constant, ast.Num, ast.Str, ast.NameConstant)):
            # Literal values (numbers, strings, booleans, None)
            pass

        elif isinstance(node, ast.List):
            # List literals for 'in' operator (e.g., "status in ['ACTIVE', 'PENDING']")
            for elt in node.elts:
                InteractionPolicyDSL._validate_ast_node(elt, permitted_attributes)

        elif isinstance(node, ast.Tuple):
            # Tuple literals
            for elt in node.elts:
                InteractionPolicyDSL._validate_ast_node(elt, permitted_attributes)

        else:
            # Reject: function calls, attribute access, subscripts, etc.
            raise DSLSyntaxError(
                f"Unsupported construct: {type(node).__name__}. "
                f"Only comparison/logical operators, literals, and variable references allowed."
            )

    @staticmethod
    def validate_condition(condition: str, permitted_attributes: set) -> None:
        """
        Validate a DSL condition against a set of permitted attributes.
        
        Args:
            condition: DSL condition string
            permitted_attributes: Set of attribute names that can be referenced
        
        Raises:
            DSLSyntaxError: If syntax invalid or unsupported constructs used
            DSLAttributeError: If undefined attribute referenced
        """
        tree = InteractionPolicyDSL.parse_condition(condition)
        InteractionPolicyDSL._validate_ast_node(tree.body, permitted_attributes)
        logger.debug(f"DSL condition validated: {condition}")

    @staticmethod
    def evaluate_condition(condition: str, uow_attributes: Dict[str, Any]) -> bool:
        """
        Evaluate a DSL condition against UOW attributes.
        
        Safe evaluation using restricted namespace (no builtins, no function calls).
        
        Args:
            condition: DSL condition string
            uow_attributes: Dict with keys: UOW_Attributes keys + reserved metadata
        
        Returns:
            bool: Result of condition evaluation
        
        Raises:
            DSLSyntaxError: If syntax invalid
            DSLAttributeError: If unauthorized attribute referenced
            Exception: If evaluation fails (missing attribute, type mismatch, etc.)
        """
        tree = InteractionPolicyDSL.parse_condition(condition)
        
        # Restrict namespace: only attributes + reserved metadata + no builtins
        safe_namespace = {
            **uow_attributes,
            "__builtins__": {},  # Prevent access to built-in functions
        }
        
        try:
            result = eval(compile(tree, "<dsl>", "eval"), {"__builtins__": {}}, safe_namespace)
            logger.debug(f"DSL condition evaluated: {condition} -> {result}")
            return bool(result)
        except KeyError as e:
            raise DSLAttributeError(f"Undefined attribute: {e}") from e
        except NameError as e:
            raise DSLAttributeError(f"Undefined attribute: {e}") from e
        except TypeError as e:
            raise ValueError(f"Type error in DSL evaluation: {e}") from e
        except Exception as e:
            raise ValueError(f"Error evaluating DSL condition: {e}") from e


def validate_interaction_policy_rules(
    policy_conditions: List[str],
    permitted_attributes: set
) -> None:
    """
    Validate all interaction_policy conditions at workflow import time.
    
    Called by workflow_manager.py during YAML import to ensure all policies
    are syntactically correct before persisting workflow data.
    
    Args:
        policy_conditions: List of DSL condition strings
        permitted_attributes: Set of permitted attribute names (UOW_Attributes + metadata)
    
    Raises:
        DSLSyntaxError: If any condition has invalid syntax
        DSLAttributeError: If any condition references unauthorized attributes
    """
    for condition in policy_conditions:
        InteractionPolicyDSL.validate_condition(condition, permitted_attributes)
    logger.info(f"Import-time DSL validation passed for {len(policy_conditions)} condition(s)")


def extract_policy_conditions_from_guardian(guardian_attributes: Dict[str, Any]) -> List[str]:
    """
    Extract all interaction_policy conditions from a Guardian's attributes.
    
    Expected format: guardian.attributes.interaction_policy = {
        "branches": [
            {"condition": "risk_score > 8", "next_interaction": "critical_queue"},
            {"condition": "risk_score <= 8", "next_interaction": "standard_queue"},
        ]
    }
    
    Args:
        guardian_attributes: The guardian.attributes dict (JSON)
    
    Returns:
        List[str]: List of condition strings
    """
    if not guardian_attributes:
        return []
    
    policy = guardian_attributes.get("interaction_policy", {})
    if not policy:
        return []
    
    branches = policy.get("branches", [])
    conditions = [branch.get("condition", "") for branch in branches if "condition" in branch]
    return [c for c in conditions if c]  # Filter out empty strings
