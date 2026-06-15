import unittest

from services.categorize import (
    CategoryResult,
    normalize_category_result,
    validate_categorize_response,
)


class TestCategorizeValidation(unittest.TestCase):
    def test_valid_response(self):
        result = validate_categorize_response(
            {
                'guessed_category_code': 'food.grocery',
                'alternatives': ['food.dining', 'unknown'],
            }
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.guessed, 'food.grocery')
        self.assertEqual(result.alternatives, ('food.dining', 'unknown'))

    def test_rejects_non_object(self):
        self.assertIsNone(validate_categorize_response(['bad']))

    def test_rejects_missing_keys(self):
        self.assertIsNone(validate_categorize_response({'guessed_category_code': 'food'}))

    def test_normalize_unknown_fallback(self):
        raw = CategoryResult(guessed='bogus.code', alternatives=('also.bogus', 'food.grocery'))
        normalized = normalize_category_result(raw)
        self.assertEqual(normalized.guessed, 'unknown')
        self.assertIn('food.grocery', normalized.alternatives)

    def test_normalize_maps_legacy_l3_codes_to_l2(self):
        raw = CategoryResult(
            guessed='food.dining.cafe',
            alternatives=('food.dining.restaurant', 'food.grocery'),
        )
        normalized = normalize_category_result(raw)
        self.assertEqual(normalized.guessed, 'food.dining')
        self.assertEqual(normalized.alternatives, ('food.grocery',))

    def test_normalize_dedupes_guess_from_alts(self):
        raw = CategoryResult(
            guessed='transport.transit',
            alternatives=('transport.transit', 'transport.fuel'),
        )
        normalized = normalize_category_result(raw)
        self.assertEqual(normalized.guessed, 'transport.transit')
        self.assertEqual(normalized.alternatives, ('transport.fuel',))


if __name__ == '__main__':
    unittest.main()
