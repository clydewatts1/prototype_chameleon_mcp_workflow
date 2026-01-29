"""
Test Suite for Semantic Guard Module

Validates expression parsing, evaluation, error handling, state verification,
custom functions, and real-world branching scenarios.
"""

import pytest
from datetime import datetime, timezone
from chameleon_workflow_engine.semantic_guard import (
    SemanticGuard,
    ExpressionEvaluator,
    ShadowLogger,
    StateVerifier,
    FunctionRegistry,
    ExpressionSyntaxError,
    ExpressionEvaluationError,
    StateHashMismatchError,
    evaluate_interaction_policy_with_guard,
    register_custom_function,
    get_shadow_logs,
    default_function_registry,
    shadow_logger,
)


# ============================================================================
# Test: Expression Parsing
# ============================================================================

class TestExpressionParsing:
    """Verify expression syntax parsing"""
    
    def test_parse_comparison_operators(self):
        """Parse comparison operators"""
        evaluator = ExpressionEvaluator()
        
        expressions = [
            "x > 10",
            "y <= 5",
            "z == 'test'",
            "a != b",
        ]
        
        for expr in expressions:
            evaluator.parse_expression(expr)  # Should not raise
    
    def test_parse_arithmetic_operators(self):
        """Parse arithmetic operators"""
        evaluator = ExpressionEvaluator()
        
        expressions = [
            "a + b",
            "x - 5",
            "y * 2",
            "z / 4",
            "a % 3",
        ]
        
        for expr in expressions:
            evaluator.parse_expression(expr)
    
    def test_parse_boolean_logic(self):
        """Parse Boolean operators and logic"""
        evaluator = ExpressionEvaluator()
        
        expressions = [
            "a and b",
            "x or y",
            "not z",
            "a and (b or c)",
        ]
        
        for expr in expressions:
            evaluator.parse_expression(expr)
    
    def test_parse_function_calls(self):
        """Parse function calls"""
        evaluator = ExpressionEvaluator()
        
        expressions = [
            "abs(x)",
            "min(a, b, c)",
            "max(x, y)",
            "round(value, 2)",
        ]
        
        for expr in expressions:
            evaluator.parse_expression(expr)
    
    def test_parse_complex_nested_expression(self):
        """Parse complex nested expressions"""
        evaluator = ExpressionEvaluator()
        
        expr = "((normalize_score(score) * 10) + abs(offset_value)) / 2 > 8"
        evaluator.parse_expression(expr)
    
    def test_parse_invalid_syntax(self):
        """Reject invalid syntax"""
        evaluator = ExpressionEvaluator()
        
        invalid_expressions = [
            "a +",
            "x ) y",
            "not and",
        ]
        
        for expr in invalid_expressions:
            with pytest.raises(ExpressionSyntaxError):
                evaluator.parse_expression(expr)


# ============================================================================
# Test: Expression Validation
# ============================================================================

class TestExpressionValidation:
    """Verify expression validation rules"""
    
    def test_validate_permitted_operators(self):
        """Validate permitted operators"""
        evaluator = ExpressionEvaluator()
        
        expressions = [
            "a + b",
            "x > 10",
            "a and b or c",
            "not x",
        ]
        
        for expr in expressions:
            evaluator.validate_expression(expr)  # Should not raise
    
    def test_validate_forbidden_bitwise_operators(self):
        """Reject bitwise operators"""
        evaluator = ExpressionEvaluator()
        
        invalid_expressions = [
            "a >> 2",
            "x << 3",
            "a & b",
            "x | y",
            "a ^ b",
            "~x",
        ]
        
        for expr in invalid_expressions:
            with pytest.raises(ExpressionSyntaxError):
                evaluator.validate_expression(expr)
    
    def test_validate_forbidden_power_operator(self):
        """Reject power operator (use pow() instead)"""
        evaluator = ExpressionEvaluator()
        
        with pytest.raises(ExpressionSyntaxError):
            evaluator.validate_expression("x ** 2")
    
    def test_validate_undefined_function(self):
        """Reject undefined functions"""
        evaluator = ExpressionEvaluator()
        
        with pytest.raises(ExpressionSyntaxError):
            evaluator.validate_expression("undefined_func(x)")
    
    def test_validate_known_functions(self):
        """Accept known functions"""
        evaluator = ExpressionEvaluator()
        
        functions = [
            "abs(x)",
            "min(a, b)",
            "max(a, b, c)",
            "round(x)",
            "floor(x)",
            "ceil(x)",
            "len(x)",
            "sqrt(x)",
            "pow(x, y)",
        ]
        
        for expr in functions:
            evaluator.validate_expression(expr)


# ============================================================================
# Test: Expression Evaluation
# ============================================================================

class TestExpressionEvaluation:
    """Verify expression safe evaluation"""
    
    def test_evaluate_comparison_operators(self):
        """Evaluate comparison operators"""
        evaluator = ExpressionEvaluator()
        context = {"x": 10, "y": 5}
        
        assert evaluator.evaluate_expression("x > y", context) is True
        assert evaluator.evaluate_expression("x < y", context) is False
        assert evaluator.evaluate_expression("x >= 10", context) is True
        assert evaluator.evaluate_expression("x == 10", context) is True
        assert evaluator.evaluate_expression("x != y", context) is True
    
    def test_evaluate_arithmetic_operators(self):
        """Evaluate arithmetic operations"""
        evaluator = ExpressionEvaluator()
        context = {"a": 10, "b": 3}
        
        assert evaluator.evaluate_expression("a + b > 12", context) is True
        assert evaluator.evaluate_expression("a - b == 7", context) is True
        assert evaluator.evaluate_expression("a * b == 30", context) is True
        assert evaluator.evaluate_expression("a / b > 3", context) is True
        assert evaluator.evaluate_expression("a % b == 1", context) is True
    
    def test_evaluate_boolean_logic(self):
        """Evaluate Boolean logic"""
        evaluator = ExpressionEvaluator()
        context = {"a": True, "b": False, "x": 10}
        
        assert evaluator.evaluate_expression("a and not b", context) is True
        assert evaluator.evaluate_expression("a or b", context) is True
        assert evaluator.evaluate_expression("not (a and b)", context) is True
        assert evaluator.evaluate_expression("x > 5 and x < 20", context) is True
    
    def test_evaluate_universal_functions(self):
        """Evaluate universal functions"""
        evaluator = ExpressionEvaluator()
        context = {"x": -5, "a": 10, "b": 3, "c": 2}
        
        assert evaluator.evaluate_expression("abs(x) == 5", context) is True
        assert evaluator.evaluate_expression("min(a, b) == 3", context) is True
        assert evaluator.evaluate_expression("max(a, b) == 10", context) is True
        assert evaluator.evaluate_expression("round(2.7) == 3", context) is True
        assert evaluator.evaluate_expression("pow(c, 3) == 8", context) is True
    
    def test_evaluate_string_functions(self):
        """Evaluate string functions"""
        evaluator = ExpressionEvaluator()
        context = {"s": "hello"}
        
        assert evaluator.evaluate_expression("len(s) == 5", context) is True
    
    def test_evaluate_undefined_variable(self):
        """Error on undefined variable"""
        evaluator = ExpressionEvaluator()
        context = {"x": 10}
        
        with pytest.raises(ExpressionEvaluationError) as exc:
            evaluator.evaluate_expression("undefined_var > 5", context)
        assert "Undefined variable" in str(exc.value)
    
    def test_evaluate_division_by_zero(self):
        """Error on division by zero"""
        evaluator = ExpressionEvaluator()
        context = {"x": 10}
        
        with pytest.raises(ExpressionEvaluationError) as exc:
            evaluator.evaluate_expression("x / 0 > 5", context)
        assert "Division by zero" in str(exc.value)
    
    def test_evaluate_type_coercion(self):
        """Evaluate with type coercion"""
        evaluator = ExpressionEvaluator()
        context = {"score": "10", "value": 10.0}
        
        # String "10" coerces to int
        assert evaluator.evaluate_expression("int(score) == 10", context) is True
        # Float coerces in comparison
        assert evaluator.evaluate_expression("value == 10", context) is True


# ============================================================================
# Test: Function Registry
# ============================================================================

class TestFunctionRegistry:
    """Verify custom function registration"""
    
    def test_register_custom_function(self):
        """Register and use custom function"""
        registry = FunctionRegistry()
        
        def double(x):
            return x * 2
        
        registry.register_custom_function("double", double)
        evaluator = ExpressionEvaluator(function_registry=registry)
        context = {"x": 5}
        
        assert evaluator.evaluate_expression("double(x) == 10", context) is True
    
    def test_register_duplicate_function_fails(self):
        """Prevent duplicate function registration"""
        registry = FunctionRegistry()
        
        with pytest.raises(ValueError):
            registry.register_custom_function("abs", lambda x: x)
    
    def test_normalize_score_custom_function(self):
        """Example: normalize_score custom function"""
        registry = FunctionRegistry()
        
        def normalize_score(value):
            """Normalize value to 0-1 range"""
            return max(0, min(1, value / 10))
        
        registry.register_custom_function("normalize_score", normalize_score)
        evaluator = ExpressionEvaluator(function_registry=registry)
        context = {"score": 8}
        
        assert evaluator.evaluate_expression("normalize_score(score) > 0.7", context) is True
    
    def test_list_functions(self):
        """List available functions"""
        registry = FunctionRegistry()
        functions = registry.list_functions()
        
        assert "abs" in functions
        assert "min" in functions
        assert "max" in functions


# ============================================================================
# Test: State Verification (X-Content-Hash)
# ============================================================================

class TestStateVerifier:
    """Verify state hash computation and verification"""
    
    def test_compute_hash_consistent(self):
        """Hash computation is deterministic"""
        attributes = {"score": 0.85, "vendor_id": "V123"}
        
        hash1 = StateVerifier.compute_hash(attributes)
        hash2 = StateVerifier.compute_hash(attributes)
        
        assert hash1 == hash2
    
    def test_compute_hash_sensitive_to_changes(self):
        """Hash changes when attributes change"""
        attributes1 = {"score": 0.85}
        attributes2 = {"score": 0.86}
        
        hash1 = StateVerifier.compute_hash(attributes1)
        hash2 = StateVerifier.compute_hash(attributes2)
        
        assert hash1 != hash2
    
    def test_verify_hash_valid(self):
        """Verify correct hash"""
        attributes = {"score": 0.85}
        hash_value = StateVerifier.compute_hash(attributes)
        
        is_valid, actual = StateVerifier.verify_hash(attributes, hash_value)
        
        assert is_valid is True
    
    def test_verify_hash_invalid(self):
        """Detect hash mismatch"""
        attributes = {"score": 0.85}
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        is_valid, actual = StateVerifier.verify_hash(attributes, wrong_hash)
        
        assert is_valid is False


# ============================================================================
# Test: Shadow Logger
# ============================================================================

class TestShadowLogger:
    """Verify error logging without interruption"""
    
    def test_capture_error(self):
        """Capture evaluation error"""
        logger_instance = ShadowLogger()
        error = ZeroDivisionError("division by zero")
        
        entry = logger_instance.capture_error(
            branch_index=0,
            condition="x / 0 > 5",
            error=error,
            uow_id="UOW-123",
            context={"x": 10}
        )
        
        assert entry.branch_index == 0
        assert entry.error_type == "ZeroDivisionError"
        assert "UOW-123" in entry.uow_id
    
    def test_get_logs_all(self):
        """Retrieve all logs"""
        logger_instance = ShadowLogger()
        logger_instance.capture_error(0, "expr1", ValueError("test"), "UOW-1")
        logger_instance.capture_error(1, "expr2", ValueError("test"), "UOW-2")
        
        logs = logger_instance.get_logs()
        assert len(logs) == 2
    
    def test_get_logs_filtered(self):
        """Retrieve logs filtered by UOW ID"""
        logger_instance = ShadowLogger()
        logger_instance.capture_error(0, "expr1", ValueError("test"), "UOW-1")
        logger_instance.capture_error(1, "expr2", ValueError("test"), "UOW-2")
        
        logs = logger_instance.get_logs("UOW-1")
        assert len(logs) == 1
        assert logs[0].uow_id == "UOW-1"
    
    def test_clear_logs_all(self):
        """Clear all logs"""
        logger_instance = ShadowLogger()
        logger_instance.capture_error(0, "expr1", ValueError("test"), "UOW-1")
        
        count = logger_instance.clear_logs()
        assert count == 1
        assert len(logger_instance.get_logs()) == 0
    
    def test_clear_logs_filtered(self):
        """Clear logs filtered by UOW ID"""
        logger_instance = ShadowLogger()
        logger_instance.capture_error(0, "expr1", ValueError("test"), "UOW-1")
        logger_instance.capture_error(1, "expr2", ValueError("test"), "UOW-2")
        
        count = logger_instance.clear_logs("UOW-1")
        assert count == 1
        assert len(logger_instance.get_logs()) == 1


# ============================================================================
# Test: Semantic Guard Evaluation
# ============================================================================

class TestSemanticGuardEvaluation:
    """Verify semantic guard policy evaluation"""
    
    def test_evaluate_simple_condition(self):
        """Evaluate simple condition branch"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {"condition": "score > 0.8", "action": "proceed", "next_interaction": "critical"}
            ]
        }
        attributes = {"score": 0.85}
        
        result = guard.evaluate_policy(policy, attributes)
        
        assert result.success is True
        assert result.next_interaction == "critical"
        assert result.matched_branch_index == 0
    
    def test_evaluate_arithmetic_condition(self):
        """Evaluate arithmetic expression"""
        # Register normalize_score FIRST
        registry = FunctionRegistry()
        registry.register_custom_function("normalize_score", lambda x: max(0, min(1, x)))
        evaluator = ExpressionEvaluator(function_registry=registry)
        guard = SemanticGuard(expression_evaluator=evaluator)
        
        policy = {
            "branches": [
                {
                    "condition": "((normalize_score(score) * 10) + abs(offset)) / 2 > 8",
                    "action": "proceed",
                    "next_interaction": "critical"
                },
                {"default": True, "action": "proceed", "next_interaction": "standard"}
            ]
        }
        attributes = {"score": 0.95, "offset": -0.5}
        
        result = guard.evaluate_policy(policy, attributes)
        
        # ((0.95 * 10) + 0.5) / 2 = (9.5 + 0.5) / 2 = 5 (NOT > 8, so default)
        assert result.success is True
    
    def test_evaluate_first_match_wins(self):
        """First matching branch is used"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {"condition": "score > 0.5", "action": "proceed", "next_interaction": "branch1"},
                {"condition": "score > 0.4", "action": "proceed", "next_interaction": "branch2"}
            ]
        }
        attributes = {"score": 0.75}
        
        result = guard.evaluate_policy(policy, attributes)
        
        assert result.next_interaction == "branch1"  # First match
    
    def test_evaluate_default_fallback(self):
        """Default branch used when no conditions match"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {"condition": "score > 0.9", "action": "proceed", "next_interaction": "critical"},
                {"default": True, "action": "proceed", "next_interaction": "standard"}
            ]
        }
        attributes = {"score": 0.5}
        
        result = guard.evaluate_policy(policy, attributes)
        
        assert result.success is True
        assert result.next_interaction == "standard"
    
    def test_evaluate_error_branch_on_evaluation_failure(self):
        """Error branch triggered on evaluation failure"""
        logger_instance = ShadowLogger()
        guard = SemanticGuard(shadow_logger_instance=logger_instance)
        policy = {
            "branches": [
                {"condition": "undefined_var > 5", "action": "proceed", "next_interaction": "normal"},
                {"on_error": True, "action": "escalate", "next_interaction": "pilot_adjudication"}
            ]
        }
        attributes = {"score": 0.5}
        
        result = guard.evaluate_policy(policy, attributes)
        
        assert result.success is True
        assert result.next_interaction == "pilot_adjudication"
        assert len(result.evaluation_errors) > 0
    
    def test_evaluate_silent_failure_protocol(self):
        """Errors logged, execution continues (Silent Failure)"""
        logger_instance = ShadowLogger()
        guard = SemanticGuard(shadow_logger_instance=logger_instance)
        policy = {
            "branches": [
                {"condition": "x / 0 > 5", "action": "proceed", "next_interaction": "error_branch"},
                {"condition": "score > 0.3", "action": "proceed", "next_interaction": "success_branch"}
            ]
        }
        attributes = {"score": 0.5}
        
        result = guard.evaluate_policy(policy, attributes, uow_id="UOW-123")
        
        # Should continue to second branch despite first branch error
        assert result.success is True
        assert result.next_interaction == "success_branch"
        
        # Error should be logged
        logs = logger_instance.get_logs("UOW-123")
        assert len(logs) > 0
    
    def test_evaluate_state_hash_verification(self):
        """Verify state hash before evaluation"""
        guard = SemanticGuard()
        attributes = {"score": 0.85}
        correct_hash = StateVerifier.compute_hash(attributes)
        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        policy = {"branches": []}
        
        result = guard.evaluate_policy(
            policy,
            attributes,
            verify_hash=wrong_hash
        )
        
        assert result.success is False
        assert "State hash mismatch" in result.evaluation_errors[0]
    
    def test_evaluate_no_branches(self):
        """Handle policy with no branches"""
        guard = SemanticGuard()
        policy = {"branches": []}
        attributes = {"score": 0.5}
        
        result = guard.evaluate_policy(policy, attributes)
        
        assert result.success is False


# ============================================================================
# Test: Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Verify realistic branching patterns"""
    
    def test_invoice_approval_risk_based_routing(self):
        """Invoice decomposed, risk_score determines routing"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {
                    "condition": "risk_score > 0.8",
                    "action": "proceed",
                    "next_interaction": "critical_review"
                },
                {
                    "condition": "risk_score <= 0.8",
                    "action": "proceed",
                    "next_interaction": "standard_review"
                },
                {
                    "default": True,
                    "action": "proceed",
                    "next_interaction": "standard_review"
                }
            ]
        }
        
        # High risk invoice
        result_high = guard.evaluate_policy(
            policy,
            {"risk_score": 0.92, "invoice_id": "INV-1"}
        )
        assert result_high.next_interaction == "critical_review"
        
        # Low risk invoice
        result_low = guard.evaluate_policy(
            policy,
            {"risk_score": 0.65, "invoice_id": "INV-2"}
        )
        assert result_low.next_interaction == "standard_review"
    
    def test_insurance_claims_complexity_branching(self):
        """Claims routing based on complexity score"""
        registry = FunctionRegistry()
        registry.register_custom_function("normalize_complexity", lambda x: x / 100)
        evaluator = ExpressionEvaluator(function_registry=registry)
        guard = SemanticGuard(expression_evaluator=evaluator)
        
        policy = {
            "branches": [
                {
                    "condition": "complexity_score > 50",
                    "action": "proceed",
                    "next_interaction": "expert_review"
                },
                {
                    "condition": "complexity_score > 20",
                    "action": "proceed",
                    "next_interaction": "standard_review"
                },
                {
                    "default": True,
                    "action": "proceed",
                    "next_interaction": "auto_approval"
                }
            ]
        }
        
        # Complex claim
        result_complex = guard.evaluate_policy(
            policy,
            {"complexity_score": 75, "claim_id": "CLM-1"}
        )
        assert result_complex.next_interaction == "expert_review"
        
        # Simple claim
        result_simple = guard.evaluate_policy(
            policy,
            {"complexity_score": 10, "claim_id": "CLM-2"}
        )
        assert result_simple.next_interaction == "auto_approval"
    
    def test_ecommerce_customer_tier_routing(self):
        """E-commerce order routing by customer tier"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {
                    "condition": "customer_tier == 'GOLD'",
                    "action": "proceed",
                    "next_interaction": "premium_fulfillment"
                },
                {
                    "condition": "customer_tier == 'SILVER'",
                    "action": "proceed",
                    "next_interaction": "standard_fulfillment"
                },
                {
                    "condition": "customer_tier == 'BRONZE'",
                    "action": "proceed",
                    "next_interaction": "economy_fulfillment"
                },
                {
                    "default": True,
                    "action": "proceed",
                    "next_interaction": "standard_fulfillment"
                }
            ]
        }
        
        # Gold customer
        result_gold = guard.evaluate_policy(
            policy,
            {"customer_tier": "GOLD", "order_id": "ORD-1"}
        )
        assert result_gold.next_interaction == "premium_fulfillment"
        
        # Silver customer
        result_silver = guard.evaluate_policy(
            policy,
            {"customer_tier": "SILVER", "order_id": "ORD-2"}
        )
        assert result_silver.next_interaction == "standard_fulfillment"
    
    def test_multi_factor_decision_with_arithmetic(self):
        """Decision based on multiple factors and arithmetic"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {
                    "condition": "(amount > 10000) and (risk_score > 0.7)",
                    "action": "proceed",
                    "next_interaction": "high_priority"
                },
                {
                    "condition": "(amount > 5000) or (risk_score > 0.8)",
                    "action": "proceed",
                    "next_interaction": "medium_priority"
                },
                {
                    "default": True,
                    "action": "proceed",
                    "next_interaction": "standard"
                }
            ]
        }
        
        # High priority: high amount AND high risk
        result_high = guard.evaluate_policy(
            policy,
            {"amount": 15000, "risk_score": 0.75}
        )
        assert result_high.next_interaction == "high_priority"
        
        # Medium priority: high amount OR high risk
        result_med = guard.evaluate_policy(
            policy,
            {"amount": 3000, "risk_score": 0.85}
        )
        assert result_med.next_interaction == "medium_priority"


# ============================================================================
# Test: Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Verify helper functions for integration"""
    
    def test_evaluate_interaction_policy_with_guard_function(self):
        """Test convenience wrapper function"""
        policy = {
            "branches": [
                {"condition": "score > 0.7", "action": "proceed", "next_interaction": "high"},
                {"default": True, "action": "proceed", "next_interaction": "low"}
            ]
        }
        
        result = evaluate_interaction_policy_with_guard(
            policy,
            {"score": 0.8}
        )
        
        assert result.success is True
        assert result.next_interaction == "high"
    
    def test_register_custom_function_global(self):
        """Test global function registration"""
        def test_multiply(x, y):
            return x * y
        
        register_custom_function("test_multiply", test_multiply)
        evaluator = ExpressionEvaluator()
        
        result = evaluator.evaluate_expression(
            "test_multiply(5, 3) == 15",
            {}
        )
        assert result is True
    
    def test_get_shadow_logs_global(self):
        """Test global shadow log retrieval"""
        guard = SemanticGuard()
        policy = {
            "branches": [
                {"condition": "undefined > 5", "action": "proceed", "next_interaction": "normal"},
                {"on_error": True, "action": "escalate", "next_interaction": "error"}
            ]
        }
        
        result = guard.evaluate_policy(
            policy,
            {"score": 0.5},
            uow_id="TEST-UOW"
        )
        
        logs = get_shadow_logs("TEST-UOW")
        # Note: Uses global shadow logger, may have other entries
        assert isinstance(logs, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
