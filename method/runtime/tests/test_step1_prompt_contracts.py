"""Keep authored Step 1 examples aligned with their actual role output contracts."""

import json
import re
import unittest

from jsonschema import Draft202012Validator

from src.common.prompt_loader import load_prompt
from src.step1_understand.review_entity_meanings import response_schema


class Step1PromptContractTests(unittest.TestCase):
    """Catch prompt files accidentally assigned to another model role."""

    def test_authored_examples_match_actual_role_schemas(self):
        """PURPOSE: Detect mismatched task instructions through their concrete output examples.
        INPUT: Authored identification and naming prompt files plus runtime role schemas.
        OUTPUT: Every example validates against the schema actually sent for that role.
        """
        roles = {'describe_entity_identification': 'identification',
                 'name_business_entity_types': 'entity_type_naming'}
        for filename, role in roles.items():
            with self.subTest(filename=filename):
                examples = re.findall(r'```json\s*\n(.*?)\n```',
                                      load_prompt('step1_understand', filename), flags=re.DOTALL)
                self.assertTrue(examples, 'Role documentation must demonstrate its output contract')
                for example in examples:
                    Draft202012Validator(response_schema(role)).validate(json.loads(example))
