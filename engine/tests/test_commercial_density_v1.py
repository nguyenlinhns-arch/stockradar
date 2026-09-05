import unittest
from scripts.verify_commercial_density_v1 import visible_main

class DisclosureDensityTests(unittest.TestCase):
    def test_closed_disclosure_counts_summary_but_open_counts_all_copy(self):
        self.assertEqual(visible_main('<main>A<details><summary>Tiêu chí</summary><p>Nội dung</p></details>B</main>'), 'A Tiêu chí B')
        for attrs in ['open', 'open=""', 'open="open"']:
            self.assertIn('Nội dung', visible_main(f'<main><details {attrs}><summary>Tiêu chí</summary><p>Nội dung</p></details></main>'))
        self.assertNotIn('Nội dung', visible_main('<main><details data-open="true"><summary>Tiêu chí</summary><p>Nội dung</p></details></main>'))
