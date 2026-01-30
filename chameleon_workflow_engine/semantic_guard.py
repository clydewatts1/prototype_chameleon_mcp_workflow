"""
Semantic Guard Module for Chameleon Workflow Engine

Implements attribute-driven branching logic with expression evaluation, error handling,
and state verification. Decouples routing decisions from execution roles (Logic-Blind).

Architecture:
- SemanticGuard: Main evaluator with expression parsing and safe evaluation
- ShadowLogger: Captures evaluation errors without interrupting execution
- Expression Evaluator: Supports arithmetic, Boolean logic, universal functions
- State Verifier: X-Content-Hash verification for UOW state consistency

References:
- docs/architecture/Branching_Logic_Guide.md
- docs/architecture/Workflow_Constitution.md (Article IX.1)
"""

import ast
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

# ============================================================================
# Exception Types
# ============================================================================


class SemanticGuardError(Exception):
    """Base exception for Semantic Guard errors"""
    pass


class ExpressionSyntaxError(SemanticGuardError):
    """Expression parsing failed"""
    pass


class ExpressionEvaluationError(SemanticGuardError):
    """Expression evaluation failed (division by zero, undefined variable, etc.)"""
    pass


class StateHashMismatchError(SemanticGuardError):
    """UOW content hash verification failed"""
    pass


# ============================================================================
# Shadow Logger
# ============================================================================


@dataclass
class ShadowLogEntry:
    """Record of an evaluation error captured by the Shadow Logger"""
    timestamp: str
    branch_index: int
    condition: str
    error_type: str
    error_message: str
    uow_id: Optional[str] = None
    variable_context: Dict[str, Any] = field(default_factory=dict)


class ShadowLogger:
    """
    Captures evaluation errors without interrupting execution.
    Implements Silent Failure Protocol: errors are logged, next branch attempted.
    """
    
    def __init__(self, max_entries: int = 10000):
        """
        Initialize Shadow Logger.
        
        Args:
            max_entries: Maximum log entries to keep in memory (FIFO eviction)
        """
        self.logs: List[ShadowLogEntry] = []
        self.max_entries = max_entries
    
    def capture_error(
        self,
        branch_index: int,
        condition: str,
        error: Exception,
        uow_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ShadowLogEntry:
        """
        Capture an evaluation error to the shadow log.
        
        Args:
            branch_index: Index of the branch that failed
            condition: The condition expression that failed
            error: The exception that was raised
            uow_id: Optional UOW ID for traceability
            context: Variable context at time of error
        
        Returns:
            ShadowLogEntry that was recorded
        """
        entry = ShadowLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            branch_index=branch_index,
            condition=condition,
            error_type=type(error).__name__,
            error_message=str(error),
            uow_id=uow_id,
            variable_context=context or {}
        )
        
        self.logs.append(entry)
        
        # FIFO eviction if exceeded max entries
        if len(self.logs) > self.max_entries:
            self.logs.pop(0)
        
        # Log to loguru for monitoring
        logger.warning(
            f"Silent failure in branch {branch_index}: {entry.error_type} - {entry.error_message}",
            error_type=entry.error_type,
            error_message=entry.error_message,
            uow_id=uow_id,
            condition=condition
        )
        
        return entry
    
    def get_logs(self, uow_id: Optional[str] = None) -> List[ShadowLogEntry]:
        """
        Retrieve log entries, optionally filtered by UOW ID.
        
        Args:
            uow_id: Optional UOW ID filter
        
        Returns:
            List of ShadowLogEntry records
        """
        if uow_id:
            return [log for log in self.logs if log.uow_id == uow_id]
        return self.logs
    
    def clear_logs(self, uow_id: Optional[str] = None) -> int:
        """
        Clear log entries, optionally filtered by UOW ID.
        
        Args:
            uow_id: Optional UOW ID filter
        
        Returns:
            Number of entries cleared
        """
        if uow_id:
            initial_count = len(self.logs)
            self.logs = [log for log in self.logs if log.uow_id != uow_id]
            return initial_count - len(self.logs)
        else:
            count = len(self.logs)
            self.logs.clear()
            return count


# Global shadow logger instance
shadow_logger = ShadowLogger()


# ============================================================================
# Function Registry
# ============================================================================


class FunctionRegistry:
    """Registry of allowed functions in semantic guard expressions"""
    
    def __init__(self):
        """Initialize with universal functions"""
        self.functions: Dict[str, Callable] = {
            # Universal functions
            'abs': abs,
            'min': min,
            'max': max,
            'round': round,
            'floor': lambda x: int(x) if x >= 0 else int(x) - 1,
            'ceil': lambda x: int(x) if x == int(x) else int(x) + 1,
            
            # String functions
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            
            # Logical aggregates
            'all': all,
            'any': any,
            
            # Statistical functions
            'sum': sum,
            'pow': pow,
            'sqrt': lambda x: x ** 0.5 if x >= 0 else float('nan'),
        }
    
    def register_custom_function(self, name: str, func: Callable) -> None:
        """
        Register a custom function for use in expressions.
        
        Args:
            name: Function name
            func: Callable function
        
        Raises:
            ValueError: If name conflicts with existing function
        """
        if name in self.functions:
            raise ValueError(f"Function '{name}' already registered")
        self.functions[name] = func
    
    def get_function(self, name: str) -> Optional[Callable]:
        """
        Get a registered function.
        
        Args:
            name: Function name
        
        Returns:
            Callable if found, None otherwise
        """
        return self.functions.get(name)
    
    def list_functions(self) -> List[str]:
        """
        List all registered function names.
        
        Returns:
            Sorted list of function names
        """
        return sorted(self.functions.keys())


# Default function registry
default_function_registry = FunctionRegistry()


# ============================================================================
# State Verifier (X-Content-Hash)
# ============================================================================


class StateVerifier:
    """
    Verifies UOW state consistency using content hash.
    Detects state drift before branching evaluation.
    """
    
    @staticmethod
    def compute_hash(uow_attributes: Dict[str, Any]) -> str:
        """
        Compute X-Content-Hash of UOW attributes.
        
        Args:
            uow_attributes: Dictionary of UOW attributes
        
        Returns:
            SHA256 hex digest of normalized JSON representation
        """
        # Normalize: sort keys, convert to JSON, hash
        normalized = json.dumps(
            uow_attributes,
            sort_keys=True,
            default=str  # Convert non-serializable types to string
        )
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    @staticmethod
    def verify_hash(
        uow_attributes: Dict[str, Any],
        expected_hash: str
    ) -> Tuple[bool, str]:
        """
        Verify UOW content hash.
        
        Args:
            uow_attributes: Current UOW attributes
            expected_hash: Expected hash to verify against
        
        Returns:
            Tuple of (is_valid, actual_hash)
        """
        actual_hash = StateVerifier.compute_hash(uow_attributes)
        return actual_hash == expected_hash, actual_hash


# ============================================================================
# Expression Evaluator
# ============================================================================


class ExpressionEvaluator:
    """
    Safe expression evaluator supporting arithmetic, Boolean logic, and functions.
    """
    
    PERMITTED_OPERATORS = {
        '+', '-', '*', '/', '%',  # Arithmetic
        'and', 'or', 'not',        # Boolean
        '<', '>', '<=', '>=', '==', '!=',  # Comparison
    }
    
    FORBIDDEN_OPERATORS = {
        '>>', '<<', '&', '|', '^', '~',  # Bitwise
        '**',  # Power (use pow() instead)
    }
    
    def __init__(self, function_registry: Optional[FunctionRegistry] = None):
        """
        Initialize expression evaluator.
        
        Args:
            function_registry: Custom function registry (uses default if None)
        """
        self.function_registry = function_registry or default_function_registry
    
    def parse_expression(self, expression: str) -> ast.Expression:
        """
        Parse expression string to AST.
        
        Args:
            expression: Python expression string
        
        Returns:
            ast.Expression node
        
        Raises:
            ExpressionSyntaxError: If expression syntax invalid
        """
        try:
            return ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise ExpressionSyntaxError(
                f"Invalid expression syntax: {expression}\n{str(e)}"
            )
    
    def validate_expression(self, expression: str) -> None:
        """
        Validate expression syntax and operator usage.
        
        Args:
            expression: Python expression string
        
        Raises:
            ExpressionSyntaxError: If validation fails
        """
        try:
            tree = self.parse_expression(expression)
        except ExpressionSyntaxError:
            raise
        
        # Walk AST and check for forbidden constructs
        self._validate_ast_node(tree.body)
    
    def _validate_ast_node(self, node: ast.AST) -> None:
        """
        Recursively validate AST node for forbidden constructs.
        
        Args:
            node: AST node to validate
        
        Raises:
            ExpressionSyntaxError: If forbidden construct found
        """
        if isinstance(node, ast.BinOp):
            op_type = type(node.op).__name__
            forbidden_ops = {
                'LShift': '>>',
                'RShift': '<<',
                'BitAnd': '&',
                'BitOr': '|',
                'BitXor': '^',
                'Pow': '**'
            }
            if op_type in forbidden_ops:
                raise ExpressionSyntaxError(
                    f"Forbidden operator: {forbidden_ops[op_type]}"
                )
        
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op).__name__
            if op_type == 'Invert':
                raise ExpressionSyntaxError("Forbidden operator: ~")
        
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self.function_registry.functions:
                    raise ExpressionSyntaxError(
                        f"Undefined function: {func_name}\n"
                        f"Available: {', '.join(self.function_registry.list_functions())}"
                    )
        
        # Recursively validate children
        for child in ast.walk(node):
            if child is not node:
                if isinstance(child, (ast.BinOp, ast.UnaryOp, ast.Call)):
                    self._validate_ast_node(child)
    
    def evaluate_expression(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Safely evaluate expression in restricted namespace.
        
        Args:
            expression: Python expression string
            context: Variable context (UOW attributes, etc.)
        
        Returns:
            Boolean result of expression
        
        Raises:
            ExpressionSyntaxError: If expression syntax invalid
            ExpressionEvaluationError: If evaluation fails
        """
        # Validate syntax first
        self.validate_expression(expression)
        
        try:
            tree = self.parse_expression(expression)
        except ExpressionSyntaxError:
            raise
        
        # Build safe namespace
        safe_namespace = {
            '__builtins__': {},  # No builtins
        }
        
        # Add context variables
        safe_namespace.update(context)
        
        # Add allowed functions
        safe_namespace.update(self.function_registry.functions)
        
        try:
            result = eval(compile(tree, '<expression>', 'eval'), safe_namespace)
            return bool(result)
        except (NameError, KeyError) as e:
            raise ExpressionEvaluationError(
                f"Undefined variable: {str(e)}"
            )
        except ZeroDivisionError:
            raise ExpressionEvaluationError("Division by zero")
        except Exception as e:
            raise ExpressionEvaluationError(
                f"Evaluation error: {type(e).__name__}: {str(e)}"
            )


# ============================================================================
# Semantic Guard
# ============================================================================


@dataclass
class BranchEvaluationResult:
    """Result of evaluating a single branch"""
    matched: bool
    branch_index: int
    next_interaction: Optional[str]
    action: str
    error: Optional[str] = None
    context_used: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardEvaluationResult:
    """Result of full semantic guard evaluation"""
    success: bool
    next_interaction: Optional[str]
    action: str
    matched_branch_index: int
    evaluation_errors: List[str] = field(default_factory=list)
    context_hash: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Dynamic Context Injection (DCI) fields
    mutation_payload: Optional[Dict[str, Any]] = None  # Contains model_override, instructions, knowledge_fragments


class SemanticGuard:
    """
    Main semantic guard evaluator.
    Handles attribute-driven branching with error handling and state verification.
    """
    
    def __init__(
        self,
        expression_evaluator: Optional[ExpressionEvaluator] = None,
        shadow_logger_instance: Optional[ShadowLogger] = None
    ):
        """
        Initialize semantic guard.
        
        Args:
            expression_evaluator: Custom expression evaluator (uses default if None)
            shadow_logger_instance: Custom shadow logger (uses global if None)
        """
        self.evaluator = expression_evaluator or ExpressionEvaluator()
        self.shadow_logger = shadow_logger_instance or shadow_logger
    
    def evaluate_policy(
        self,
        policy: Dict[str, Any],
        uow_attributes: Dict[str, Any],
        uow_id: Optional[str] = None,
        verify_hash: Optional[str] = None
    ) -> GuardEvaluationResult:
        """
        Evaluate interaction_policy against UOW attributes.
        
        Args:
            policy: interaction_policy dict with branches array
            uow_attributes: Current UOW attributes
            uow_id: Optional UOW ID for traceability
            verify_hash: Optional X-Content-Hash to verify before evaluation
        
        Returns:
            GuardEvaluationResult with routing decision
        """
        # Verify state hash if provided
        if verify_hash:
            is_valid, actual_hash = StateVerifier.verify_hash(
                uow_attributes,
                verify_hash
            )
            if not is_valid:
                logger.error(
                    f"State hash mismatch for UOW {uow_id}: "
                    f"expected {verify_hash[:16]}..., got {actual_hash[:16]}...",
                    uow_id=uow_id
                )
                return GuardEvaluationResult(
                    success=False,
                    next_interaction=None,
                    action="error",
                    matched_branch_index=-1,
                    evaluation_errors=["State hash mismatch - potential drift"],
                    context_hash=actual_hash
                )
        
        # Compute current hash
        current_hash = StateVerifier.compute_hash(uow_attributes)
        
        # Extract branches array
        branches = policy.get('branches', [])
        if not branches:
            return GuardEvaluationResult(
                success=False,
                next_interaction=None,
                action="error",
                matched_branch_index=-1,
                evaluation_errors=["No branches defined in policy"],
                context_hash=current_hash
            )
        
        # Track errors for error handling branch
        evaluation_errors = []
        default_branch = None
        error_branch = None
        
        # Evaluate branches sequentially (first match wins)
        for branch_index, branch in enumerate(branches):
            # Check for on_error flag (error handler)
            if branch.get('on_error', False):
                error_branch = (branch_index, branch)
                continue
            
            # Check for default flag (fallback)
            if branch.get('default', False):
                default_branch = (branch_index, branch)
                continue
            
            # Regular branch: evaluate condition
            condition = branch.get('condition')
            if not condition:
                continue
            
            try:
                # Evaluate condition with UOW attributes as context
                matches = self.evaluator.evaluate_expression(
                    condition,
                    uow_attributes
                )
                
                if matches:
                    # Condition matched - return this branch
                    action = branch.get('action', 'proceed')
                    
                    # Extract mutation payload if action is 'mutate' (for DCI)
                    mutation_payload = None
                    if action == 'mutate':
                        mutation_payload = branch.get('payload', {})
                    
                    return GuardEvaluationResult(
                        success=True,
                        next_interaction=branch.get('next_interaction'),
                        action=action,
                        matched_branch_index=branch_index,
                        context_hash=current_hash,
                        mutation_payload=mutation_payload
                    )
            
            except (ExpressionSyntaxError, ExpressionEvaluationError) as e:
                # Silent failure: log error and continue
                self.shadow_logger.capture_error(
                    branch_index=branch_index,
                    condition=condition,
                    error=e,
                    uow_id=uow_id,
                    context=uow_attributes
                )
                evaluation_errors.append(str(e))
        
        # No regular branch matched
        # Check for error branch if any errors occurred
        if evaluation_errors and error_branch:
            branch_index, branch = error_branch
            return GuardEvaluationResult(
                success=True,
                next_interaction=branch.get('next_interaction'),
                action=branch.get('action', 'escalate'),
                matched_branch_index=branch_index,
                evaluation_errors=evaluation_errors,
                context_hash=current_hash
            )
        
        # Use default branch if available
        if default_branch:
            branch_index, branch = default_branch
            return GuardEvaluationResult(
                success=True,
                next_interaction=branch.get('next_interaction'),
                action=branch.get('action', 'proceed'),
                matched_branch_index=branch_index,
                evaluation_errors=evaluation_errors,
                context_hash=current_hash
            )
        
        # No match, no error handler, no default
        return GuardEvaluationResult(
            success=False,
            next_interaction=None,
            action="error",
            matched_branch_index=-1,
            evaluation_errors=evaluation_errors + ["No matching branch and no default"],
            context_hash=current_hash
        )


# ============================================================================
# Helper Functions for Integration
# ============================================================================


def evaluate_interaction_policy_with_guard(
    policy: Dict[str, Any],
    uow_attributes: Dict[str, Any],
    uow_id: Optional[str] = None,
    verify_hash: Optional[str] = None
) -> GuardEvaluationResult:
    """
    Convenience function to evaluate interaction_policy using default guard.
    
    Args:
        policy: interaction_policy dict
        uow_attributes: UOW attributes
        uow_id: Optional UOW ID
        verify_hash: Optional X-Content-Hash for verification
    
    Returns:
        GuardEvaluationResult
    """
    guard = SemanticGuard()
    return guard.evaluate_policy(
        policy=policy,
        uow_attributes=uow_attributes,
        uow_id=uow_id,
        verify_hash=verify_hash
    )


def register_custom_function(name: str, func: Callable) -> None:
    """
    Register a custom function globally.
    
    Args:
        name: Function name
        func: Callable function
    """
    default_function_registry.register_custom_function(name, func)


def get_shadow_logs(uow_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve shadow logs for audit trail.
    
    Args:
        uow_id: Optional UOW ID filter
    
    Returns:
        List of log dictionaries
    """
    logs = shadow_logger.get_logs(uow_id)
    return [
        {
            'timestamp': log.timestamp,
            'branch_index': log.branch_index,
            'condition': log.condition,
            'error_type': log.error_type,
            'error_message': log.error_message,
            'uow_id': log.uow_id,
            'context_sample': {k: v for k, v in log.variable_context.items() if k in ['score', 'risk_score', 'previous_batch_score']}
        }
        for log in logs
    ]
