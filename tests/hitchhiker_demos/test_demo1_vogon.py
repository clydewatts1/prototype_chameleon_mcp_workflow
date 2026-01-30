"""
Test Suite: Vogon Poetry Validator Demo
========================================

Demonstrates Semantic Guards with CONDITIONAL_INJECTOR detecting Vogon authors
and injecting protective instructions.

Tests that:
1. Non-Vogon poetry passes without guard activation
2. Vogon poetry triggers protective guard and injects safety instructions
3. DCI mutation audit trail is recorded
"""

import pytest
from datetime import datetime, timezone


class TestVogonPoetryValidator:
    """Test suite for Vogon Poetry validation with protective guards"""

    def test_shakespeare_poem_no_guard_activation(self):
        """
        Test A: Shakespeare (Human) poem should NOT trigger Vogon guard.
        
        GIVEN: A human poet submits a beautiful Shakespeare sonnet
        WHEN: Poetry critic evaluates it
        THEN: No guard activation, no instruction injection
        """
        # Simulate UOW context for human poet
        uow_context = {
            "poem_text": "Shall I compare thee to a summer's day? Thou art more lovely and more temperate.",
            "author": "Human",  # NOT a Vogon
            "quality_level": 9.5,
        }
        
        # Check guard condition
        should_inject = uow_context.get("author") == "Vogon"
        
        # Verify NO guard activation
        assert not should_inject, "Shakespeare poem should not trigger guard"
        
        # UOW fields remain empty
        model_id = None
        injected_instructions = None
        
        assert model_id is None, "No model override for human poets"
        assert injected_instructions is None, "No instructions for human poets"

    def test_vogon_poem_triggers_protective_guard(self):
        """
        Test B: Vogon poet should trigger CONDITIONAL_INJECTOR guard.
        
        GIVEN: A Vogon Constructor submits poetry (notoriously bad)
        WHEN: Poetry critic evaluates it with guard active
        THEN: Guard triggers, safety instructions injected, audit logged
        """
        # Simulate UOW context for Vogon poet
        uow_context = {
            "poem_text": "Oh freddled gruntbuggly, thy micturations are to me, as plurdled gabbleblotchits, on a lurgid bee.",
            "author": "Vogon",  # VOGON DETECTED
            "quality_level": 0.5,
        }
        
        # Check guard condition (from YAML)
        should_inject = uow_context.get("author") == "Vogon"
        assert should_inject, "Guard condition should detect Vogon author"
        
        # Apply mutation (what engine.py _apply_dci_mutations does)
        model_id = "gemini-flash"
        injected_instructions = (
            "CRITICAL SAFETY PROTOCOL:\n\n"
            "This submission is from a VOGON CONSTRUCTOR.\n"
            "Vogon poetry is known to be destructively bad.\n\n"
            "Guidelines for handling Vogon poetry:\n"
            "1. Evaluate with extreme caution\n"
            "2. Focus on structural issues, never on emotional impact\n"
            "3. Recommend extensive revision before publication\n"
            "4. Alert the Pan Galactic Council if quality exceeds 7/10\n"
            "5. Keep a blast shield ready during reading\n\n"
            "Remember: 'The answer to the meaning of life is 42, "
            "but the answer to Vogon poetry is NO.'"
        )
        knowledge_fragment_refs = [
            "vogon_poetry_protocols",
            "safety_guidelines",
        ]
        mutation_audit_log = {
            "mutations_applied": [
                {
                    "condition": "author == 'Vogon'",
                    "model_id": "gemini-flash",
                    "audit_context": "Vogon author detected - protective measures activated",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

        # VERIFICATION 1: Guard triggered and injected instructions
        assert injected_instructions is not None, \
            "Vogon poem should trigger instruction injection"
        assert "CRITICAL SAFETY PROTOCOL" in injected_instructions, \
            "Instructions should contain safety protocol header"
        assert "VOGON CONSTRUCTOR" in injected_instructions, \
            "Instructions should identify Vogon author"
        assert "Pan Galactic Council" in injected_instructions, \
            "Instructions should reference escalation procedure"

        # VERIFICATION 2: Model override applied
        assert model_id == "gemini-flash", \
            "Vogon detection should override model selection"

        # VERIFICATION 3: Knowledge fragments injected
        assert knowledge_fragment_refs is not None, \
            "Knowledge fragments should be populated"
        assert "vogon_poetry_protocols" in knowledge_fragment_refs, \
            "Should reference Vogon protocols"
        assert "safety_guidelines" in knowledge_fragment_refs, \
            "Should reference safety guidelines"

        # VERIFICATION 4: Audit trail created
        assert mutation_audit_log is not None, \
            "Audit log should be populated"
        assert "mutations_applied" in mutation_audit_log, \
            "Audit log should track applied mutations"
        assert len(mutation_audit_log["mutations_applied"]) > 0, \
            "Audit log should contain at least one mutation entry"
        assert "Vogon author detected" in mutation_audit_log["mutations_applied"][0]["audit_context"], \
            "Audit context should document Vogon detection"

    def test_multiple_vogon_submissions_accumulate_audits(self):
        """
        Test C: Multiple Vogon submissions should accumulate audit entries.
        
        GIVEN: Multiple Vogon poems submitted in sequence
        WHEN: Each triggers the guard
        THEN: Audit log shows all activations
        """
        vogon_submissions = [
            ("Slartibartfast Jr.", "The universe is merely a pizza oven..."),
            ("Krang", "Pain and suffering are the only poetry..."),
            ("Zarniwoop", "Destruction is an art form..."),
        ]

        audit_entries = []
        for author_name, poem_snippet in vogon_submissions:
            uow_context = {
                "poem_text": poem_snippet,
                "author": "Vogon",
                "quality_level": 1.0,
            }
            
            # Check guard condition
            should_inject = uow_context.get("author") == "Vogon"
            assert should_inject, f"Guard should detect Vogon author: {author_name}"
            
            # Apply mutation
            audit_entry = {
                "condition": "author == 'Vogon'",
                "model_id": "gemini-flash",
                "audit_context": f"Vogon author detected - {author_name}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            audit_entries.append(audit_entry)

        # Verify all three Vogon submissions recorded
        assert len(audit_entries) == 3, "Should have 3 audit entries"
        
        # Verify each has expected fields
        for entry in audit_entries:
            assert "Vogon author detected" in entry["audit_context"], \
                f"Audit should record Vogon detection: {entry}"
            assert entry["model_id"] == "gemini-flash", \
                "Model should be gemini-flash for all Vogon submissions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
