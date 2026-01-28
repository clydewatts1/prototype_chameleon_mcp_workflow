"""
Tests for Interaction Policy DSL Evaluator

Validates DSL parsing, validation, and evaluation against the specification:
- Article IX.1: Interaction Policy Evaluation (Workflow_Constitution.md)
- R11: DSL Syntax Validation (Workflow_Import_Requirements.md)
- R12: Multi-OUTBOUND Policy Requirement (Workflow_Import_Requirements.md)

Tests cover:
1. Valid DSL syntax and evaluation
2. Invalid syntax detection
3. Unauthorized attribute rejection
4. Safe namespace enforcement
5. Edge cases and error handling
"""

import pytest
from chameleon_workflow_engine.dsl_evaluator import (
    InteractionPolicyDSL,
    DSLSyntaxError,
    DSLAttributeError,
    validate_interaction_policy_rules,
    extract_policy_conditions_from_guardian,
)


class TestDSLParsing:
    """Test DSL condition parsing."""

    def test_valid_simple_comparison(self):
        """Test parsing simple comparison operators."""
        conditions = [
            "risk_score > 8",
            "amount >= 1000",
            "count <= 5",
            "threshold < 100",
            "status == 'ACTIVE'",
            "is_flagged != True",
        ]
        for condition in conditions:
            # Should not raise
            tree = InteractionPolicyDSL.parse_condition(condition)
            assert tree is not None

    def test_valid_logical_operators(self):
        """Test parsing logical operators."""
        conditions = [
            "risk_score > 8 and not is_flagged",
            "amount >= 1000 or is_priority",
            "status == 'ACTIVE' and child_count <= 5",
            "not (is_blocked and is_flagged)",
        ]
        for condition in conditions:
            tree = InteractionPolicyDSL.parse_condition(condition)
            assert tree is not None

    def test_valid_in_operator(self):
        """Test parsing 'in' membership operator."""
        conditions = [
            "status in ['ACTIVE', 'PENDING']",
            "priority in ('HIGH', 'CRITICAL')",
        ]
        for condition in conditions:
            tree = InteractionPolicyDSL.parse_condition(condition)
            assert tree is not None

    def test_invalid_syntax_unbalanced_parentheses(self):
        """Test rejection of unbalanced parentheses."""
        with pytest.raises(DSLSyntaxError):
            InteractionPolicyDSL.parse_condition("(risk_score > 8 and is_active")

    def test_invalid_syntax_bad_operator(self):
        """Test rejection of invalid operators during validation."""
        permitted = {"risk_score"}
        # >> (bitwise shift) is syntactically valid Python, but not allowed in DSL
        with pytest.raises(DSLSyntaxError):
            InteractionPolicyDSL.validate_condition("risk_score >> 8", permitted)

    def test_invalid_syntax_incomplete_expression(self):
        """Test rejection of incomplete expressions."""
        with pytest.raises(DSLSyntaxError):
            InteractionPolicyDSL.parse_condition("risk_score >")  # Missing right operand


class TestDSLValidation:
    """Test DSL condition validation against permitted attributes."""

    def test_valid_uow_attribute_reference(self):
        """Test validation allows UOW_Attributes."""
        permitted = {"risk_score", "amount", "is_flagged", "priority"}
        # Should not raise
        InteractionPolicyDSL.validate_condition("risk_score > 8", permitted)
        InteractionPolicyDSL.validate_condition("amount >= 1000 and not is_flagged", permitted)

    def test_valid_reserved_metadata_reference(self):
        """Test validation allows reserved metadata."""
        permitted = InteractionPolicyDSL.RESERVED_METADATA
        # Should not raise
        InteractionPolicyDSL.validate_condition("child_count <= 5", permitted)
        InteractionPolicyDSL.validate_condition("status == 'ACTIVE'", permitted)
        InteractionPolicyDSL.validate_condition("parent_id != None", permitted)

    def test_mixed_attributes_and_metadata(self):
        """Test validation allows mixed UOW_Attributes and reserved metadata."""
        permitted = {"risk_score", "amount"} | InteractionPolicyDSL.RESERVED_METADATA
        # Should not raise
        InteractionPolicyDSL.validate_condition(
            "risk_score > 8 and child_count <= 5",
            permitted
        )
        InteractionPolicyDSL.validate_condition(
            "amount >= 1000 and status == 'ACTIVE'",
            permitted
        )

    def test_unauthorized_attribute_rejection(self):
        """Test validation rejects undefined attributes."""
        permitted = {"risk_score", "amount"}
        with pytest.raises(DSLAttributeError):
            InteractionPolicyDSL.validate_condition("undefined_attr > 10", permitted)

    def test_actor_id_rejection(self):
        """Test validation rejects actor_id (security boundary)."""
        permitted = InteractionPolicyDSL.RESERVED_METADATA
        # actor_id is NOT in reserved metadata, should be rejected
        with pytest.raises(DSLAttributeError):
            InteractionPolicyDSL.validate_condition("actor_id == 'user123'", permitted)

    def test_function_call_rejection(self):
        """Test validation rejects function calls."""
        permitted = {"risk_score"} | InteractionPolicyDSL.RESERVED_METADATA
        with pytest.raises(DSLSyntaxError):
            InteractionPolicyDSL.validate_condition("max(risk_score, 5) > 8", permitted)

    def test_builtin_function_rejection(self):
        """Test validation rejects built-in functions."""
        permitted = {"risk_score"} | InteractionPolicyDSL.RESERVED_METADATA
        with pytest.raises(DSLSyntaxError):
            InteractionPolicyDSL.validate_condition("len(status) > 5", permitted)

    def test_attribute_access_rejection(self):
        """Test validation rejects attribute access syntax."""
        permitted = {"obj"} | InteractionPolicyDSL.RESERVED_METADATA
        with pytest.raises(DSLSyntaxError):
            InteractionPolicyDSL.validate_condition("obj.field > 10", permitted)


class TestDSLEvaluation:
    """Test DSL condition evaluation against runtime data."""

    def test_simple_comparison_evaluation(self):
        """Test evaluation of simple comparisons."""
        attributes = {"risk_score": 9, "amount": 1500, "is_flagged": False}

        assert InteractionPolicyDSL.evaluate_condition("risk_score > 8", attributes) is True
        assert InteractionPolicyDSL.evaluate_condition("risk_score > 10", attributes) is False
        assert InteractionPolicyDSL.evaluate_condition("amount >= 1000", attributes) is True
        assert InteractionPolicyDSL.evaluate_condition("amount <= 1000", attributes) is False

    def test_string_comparison_evaluation(self):
        """Test evaluation of string comparisons."""
        attributes = {"status": "ACTIVE"}

        assert InteractionPolicyDSL.evaluate_condition("status == 'ACTIVE'", attributes) is True
        assert InteractionPolicyDSL.evaluate_condition("status == 'PENDING'", attributes) is False
        assert InteractionPolicyDSL.evaluate_condition("status != 'FAILED'", attributes) is True

    def test_logical_and_evaluation(self):
        """Test evaluation of AND logic."""
        attributes = {"risk_score": 9, "is_flagged": False}

        # Both conditions true
        assert (
            InteractionPolicyDSL.evaluate_condition(
                "risk_score > 8 and not is_flagged", attributes
            ) is True
        )

        # One condition false
        assert (
            InteractionPolicyDSL.evaluate_condition(
                "risk_score > 8 and is_flagged", attributes
            ) is False
        )

    def test_logical_or_evaluation(self):
        """Test evaluation of OR logic."""
        attributes = {"risk_score": 9, "is_priority": False}

        # At least one true
        assert (
            InteractionPolicyDSL.evaluate_condition(
                "risk_score > 8 or is_priority", attributes
            ) is True
        )

        # Both false
        assert (
            InteractionPolicyDSL.evaluate_condition(
                "risk_score < 5 or is_priority", attributes
            ) is False
        )

    def test_logical_not_evaluation(self):
        """Test evaluation of NOT logic."""
        attributes = {"is_flagged": True, "is_blocked": False}

        assert InteractionPolicyDSL.evaluate_condition("not is_flagged", attributes) is False
        assert InteractionPolicyDSL.evaluate_condition("not is_blocked", attributes) is True

    def test_reserved_metadata_evaluation(self):
        """Test evaluation with reserved metadata."""
        attributes = {
            "child_count": 3,
            "finished_child_count": 2,
            "status": "ACTIVE",
            "uow_id": "uuid-123",
            "parent_id": None,
        }

        assert InteractionPolicyDSL.evaluate_condition("child_count <= 5", attributes) is True
        assert InteractionPolicyDSL.evaluate_condition("status == 'ACTIVE'", attributes) is True
        assert InteractionPolicyDSL.evaluate_condition("parent_id == None", attributes) is True

    def test_in_operator_evaluation(self):
        """Test evaluation of 'in' membership operator."""
        attributes = {"status": "ACTIVE", "priority": "HIGH"}

        assert (
            InteractionPolicyDSL.evaluate_condition(
                "status in ['ACTIVE', 'PENDING']", attributes
            ) is True
        )
        assert (
            InteractionPolicyDSL.evaluate_condition(
                "priority in ('LOW', 'MEDIUM')", attributes
            ) is False
        )

    def test_complex_expression_evaluation(self):
        """Test evaluation of complex multi-operator expressions."""
        attributes = {
            "risk_score": 8.5,
            "amount": 1500,
            "is_flagged": False,
            "child_count": 3,
        }

        # Complex condition: high risk AND high amount OR few children
        assert (
            InteractionPolicyDSL.evaluate_condition(
                "(risk_score > 8 and amount > 1000) or child_count <= 2",
                attributes,
            ) is True
        )

    def test_missing_attribute_error(self):
        """Test error when condition references missing attribute."""
        attributes = {"risk_score": 9}

        # undefined_attr not in attributes
        with pytest.raises(DSLAttributeError):
            InteractionPolicyDSL.evaluate_condition("undefined_attr > 10", attributes)

    def test_type_mismatch_error(self):
        """Test error on type mismatch in comparison."""
        attributes = {"status": "ACTIVE"}

        # Comparing string to number (should raise TypeError)
        with pytest.raises(ValueError):
            InteractionPolicyDSL.evaluate_condition("status > 100", attributes)

    def test_safe_namespace_no_builtins(self):
        """Test that evaluation cannot access Python builtins."""
        attributes = {"risk_score": 9}

        # Attempting to call built-in function should fail
        with pytest.raises((DSLSyntaxError, ValueError)):
            InteractionPolicyDSL.evaluate_condition("len(status) > 5", attributes)


class TestBatchValidation:
    """Test batch validation of multiple policy conditions."""

    def test_validate_multiple_conditions(self):
        """Test validation of multiple conditions."""
        conditions = [
            "risk_score > 8",
            "amount >= 1000 and not is_flagged",
            "status == 'ACTIVE'",
        ]
        permitted = {"risk_score", "amount", "is_flagged", "status"}

        # Should not raise
        validate_interaction_policy_rules(conditions, permitted)

    def test_batch_validation_with_invalid_condition(self):
        """Test batch validation stops on first invalid condition."""
        conditions = [
            "risk_score > 8",
            "undefined_attr > 10",  # Invalid
            "status == 'ACTIVE'",
        ]
        permitted = {"risk_score", "status"}

        with pytest.raises(DSLAttributeError):
            validate_interaction_policy_rules(conditions, permitted)


class TestPolicyExtractionFromGuardian:
    """Test extraction of policy conditions from Guardian attributes."""

    def test_extract_conditions_from_guardian(self):
        """Test extracting conditions from Guardian attributes."""
        guardian_attributes = {
            "interaction_policy": {
                "branches": [
                    {
                        "condition": "risk_score > 8",
                        "next_interaction": "critical_queue",
                    },
                    {
                        "condition": "risk_score <= 8",
                        "next_interaction": "standard_queue",
                    },
                ]
            }
        }

        conditions = extract_policy_conditions_from_guardian(guardian_attributes)
        assert len(conditions) == 2
        assert "risk_score > 8" in conditions
        assert "risk_score <= 8" in conditions

    def test_extract_conditions_empty_guardian(self):
        """Test extraction from guardian without policy."""
        conditions = extract_policy_conditions_from_guardian({})
        assert conditions == []

    def test_extract_conditions_none_guardian(self):
        """Test extraction from None guardian."""
        conditions = extract_policy_conditions_from_guardian(None)
        assert conditions == []


class TestRealWorldScenarios:
    """Test realistic policy evaluation scenarios."""

    def test_invoice_approval_routing(self):
        """Test invoice approval scenario: risk-based routing."""
        # Invoice analysis produces risk_score
        attributes = {
            "risk_score": 0.85,  # 85% risk
            "amount": 50000,
            "is_flagged": False,
            "child_count": 5,
        }
        permitted = {"risk_score", "amount", "is_flagged", "child_count"}

        # Policy: high risk → critical queue
        policy_1 = "risk_score > 0.8"
        policy_2 = "risk_score <= 0.8"

        validate_interaction_policy_rules([policy_1, policy_2], permitted)

        # Evaluation
        assert InteractionPolicyDSL.evaluate_condition(policy_1, attributes) is True
        assert InteractionPolicyDSL.evaluate_condition(policy_2, attributes) is False

    def test_claim_processing_routing(self):
        """Test insurance claim processing: complexity-based routing."""
        attributes = {
            "claim_complexity": "HIGH",
            "claim_amount": 100000,
            "requires_investigation": True,
            "child_count": 10,
            "finished_child_count": 10,
        }
        permitted = attributes.keys() | InteractionPolicyDSL.RESERVED_METADATA

        # Policy: high complexity and high amount → investigation queue
        policy = "claim_amount > 50000 and claim_complexity == 'HIGH'"

        validate_interaction_policy_rules([policy], permitted)
        assert InteractionPolicyDSL.evaluate_condition(policy, attributes) is True

    def test_order_fulfillment_routing(self):
        """Test e-commerce order fulfillment: multi-branch routing."""
        attributes = {
            "order_value": 250,
            "priority": "STANDARD",
            "is_international": False,
            "child_count": 3,
        }
        permitted = attributes.keys() | InteractionPolicyDSL.RESERVED_METADATA

        # Multiple policies for different fulfillment paths
        policies = [
            "order_value > 500 and priority == 'EXPRESS'",  # Express path
            "order_value > 100 and not is_international",  # Standard domestic
            "is_international",  # International path
        ]

        validate_interaction_policy_rules(policies, permitted)

        # Evaluation
        assert InteractionPolicyDSL.evaluate_condition(policies[0], attributes) is False
        assert InteractionPolicyDSL.evaluate_condition(policies[1], attributes) is True
        assert InteractionPolicyDSL.evaluate_condition(policies[2], attributes) is False
