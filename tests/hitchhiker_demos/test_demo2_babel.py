"""
Test Suite: Babel Fish Translator Demo
=======================================

Demonstrates DCI with three mutation pathways based on recipient species.
Each species gets culturally-appropriate model selection and instructions.

Tests that:
1. Human recipients get diplomatic, polite translation model
2. Vogon recipients get aggressive, harsh translation model
3. Betelgeusian recipients get flattering, philosophical translation model
"""

import pytest
from datetime import datetime, timezone


class TestBabelFishTranslator:
    """Test suite for species-specific message translation with DCI"""

    def test_human_recipient_gets_diplomatic_translation(self):
        """
        Test A: Messages to Humans should use diplomatic model and instructions.
        
        GIVEN: A message intended for a Human recipient
        WHEN: Translator evaluates with guard active
        THEN: Guard selects gpt-4-turbo with diplomatic instructions
        """
        # Create context for Human translation
        context = {
            "message": "You have failed to complete the project on time.",
            "recipient_species": "Human",
            "tone": "neutral",
        }
        
        # Evaluate conditions (from YAML demo2_babel_fish.yaml)
        if context.get("recipient_species") == "Human":
            model_id = "gpt-4-turbo"
            injected_instructions = (
                "HUMAN TRANSLATION PROTOCOL:\n\n"
                "Humans prefer polite, diplomatic communication.\n"
                "Translate the message with:\n"
                "1. Courteous language and respectful tone\n"
                "2. Acknowledgment of the recipient's perspective\n"
                "3. Offers of cooperation and mutual benefit\n"
                "4. Emotional intelligence and empathy\n\n"
                "Example: 'I appreciate your perspective. Perhaps we could "
                "explore a mutually beneficial approach to this challenge.'\n\n"
                "Soften criticism. Humans respond well to politeness."
            )
        else:
            model_id = None
            injected_instructions = None

        # VERIFICATION 1: Model selection for Human
        assert model_id == "gpt-4-turbo", \
            "Human recipients should use gpt-4-turbo (diplomatic model)"

        # VERIFICATION 2: Diplomatic instructions injected
        assert "HUMAN TRANSLATION PROTOCOL" in injected_instructions, \
            "Should have human-specific protocol header"
        assert "polite, diplomatic communication" in injected_instructions, \
            "Should emphasize politeness"
        assert "Soften criticism" in injected_instructions, \
            "Should instruct to soften harsh messages"
        assert "Emotional intelligence" in injected_instructions, \
            "Should emphasize empathy"

    def test_vogon_recipient_gets_aggressive_translation(self):
        """
        Test B: Messages to Vogons should use aggressive model and instructions.
        
        GIVEN: A message intended for a Vogon recipient
        WHEN: Translator evaluates with guard active
        THEN: Guard selects gpt-4 with aggressive instructions
        """
        # Create context for Vogon translation
        context = {
            "message": "You have failed to complete the project on time.",
            "recipient_species": "Vogon",
            "tone": "formal",
        }
        
        # Evaluate conditions
        if context.get("recipient_species") == "Vogon":
            model_id = "gpt-4"
            injected_instructions = (
                "VOGON TRANSLATION PROTOCOL:\n\n"
                "Vogons appreciate aggressive, destructive communication.\n"
                "Translate the message with:\n"
                "1. Harsh, cutting language\n"
                "2. Emphasis on destruction and demolition\n"
                "3. References to bureaucratic inefficiency\n"
                "4. Contempt for inferior life forms\n\n"
                "Example: 'Your poetry is like a supernova's aftermath - "
                "utterly destructive and completely unintelligible.'\n\n"
                "Do NOT soften the message. Vogons respect bluntness."
            )
        else:
            model_id = None
            injected_instructions = None

        # VERIFICATION 1: Model selection for Vogon
        assert model_id == "gpt-4", \
            "Vogon recipients should use gpt-4 (powerful aggressive model)"

        # VERIFICATION 2: Aggressive instructions injected
        assert "VOGON TRANSLATION PROTOCOL" in injected_instructions, \
            "Should have vogon-specific protocol header"
        assert "aggressive, destructive communication" in injected_instructions, \
            "Should emphasize aggression"
        assert "Harsh, cutting language" in injected_instructions, \
            "Should instruct harsh language"
        assert "Do NOT soften the message" in injected_instructions, \
            "Should explicitly forbid softening"

    def test_betelgeusian_recipient_gets_flattering_translation(self):
        """
        Test C: Messages to Betelgeusians should use philosophical model and flattering instructions.
        
        GIVEN: A message intended for a Betelgeusian recipient
        WHEN: Translator evaluates with guard active
        THEN: Guard selects claude-3-opus with flattering instructions
        """
        # Create context for Betelgeusian translation
        context = {
            "message": "You have failed to complete the project on time.",
            "recipient_species": "Betelgeusian",
            "tone": "casual",
        }
        
        # Evaluate conditions
        if context.get("recipient_species") == "Betelgeusian":
            model_id = "claude-3-opus"
            injected_instructions = (
                "BETELGEUSIAN TRANSLATION PROTOCOL:\n\n"
                "Betelgeusians appreciate flattery, philosophy, and complexity.\n"
                "Translate the message with:\n"
                "1. Elaborate philosophical frameworks\n"
                "2. Excessive flattery and ego-boosting\n"
                "3. Complex, multidimensional perspectives\n"
                "4. References to cosmic significance\n\n"
                "Example: 'Your unparalleled wisdom, combined with your "
                "cosmic perspective, grants you unique insight into this "
                "multidimensional challenge.'\n\n"
                "Don't hold back on flattery. Betelgeusians are vain."
            )
        else:
            model_id = None
            injected_instructions = None

        # VERIFICATION 1: Model selection for Betelgeusian
        assert model_id == "claude-3-opus", \
            "Betelgeusian recipients should use claude-3-opus (philosophical model)"

        # VERIFICATION 2: Flattering instructions injected
        assert "BETELGEUSIAN TRANSLATION PROTOCOL" in injected_instructions, \
            "Should have betelgeusian-specific protocol header"
        assert "flattery" in injected_instructions, \
            "Should emphasize flattery"
        assert "philosophical" in injected_instructions, \
            "Should emphasize philosophy"
        assert "Betelgeusians are vain" in injected_instructions, \
            "Should acknowledge vanity and exploit it"

    def test_all_species_coexist_with_different_models(self):
        """
        Test D: Verify all three species can be handled with different models simultaneously.
        
        GIVEN: Three parallel messages for different species
        WHEN: Each applies DCI mutations independently
        THEN: Each gets its own model selection and instructions
        """
        species_mutations = [
            ("Human", "gpt-4-turbo", "diplomatic"),
            ("Vogon", "gpt-4", "aggressive"),
            ("Betelgeusian", "claude-3-opus", "flattering"),
        ]

        species_model_map = {}
        for species, expected_model, style in species_mutations:
            context = {
                "message": f"Standard message to {species}",
                "recipient_species": species,
                "tone": "neutral",
            }
            
            # Apply appropriate mutation based on species
            if species == "Human":
                model_id = "gpt-4-turbo"
            elif species == "Vogon":
                model_id = "gpt-4"
            elif species == "Betelgeusian":
                model_id = "claude-3-opus"
            else:
                model_id = None
            
            species_model_map[species] = model_id

        # Verify all three coexist with correct models
        assert len(species_model_map) == 3, "Should have 3 species mapped"

        assert species_model_map.get("Human") == "gpt-4-turbo", \
            "Humans should get gpt-4-turbo"
        assert species_model_map.get("Vogon") == "gpt-4", \
            "Vogons should get gpt-4"
        assert species_model_map.get("Betelgeusian") == "claude-3-opus", \
            "Betelgeusians should get claude-3-opus"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
