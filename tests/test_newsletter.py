import unittest

import newsletter


class NewsletterBlockTests(unittest.TestCase):
    def setUp(self):
        self.user = newsletter.BUTTONDOWN_USER

    def tearDown(self):
        newsletter.BUTTONDOWN_USER = self.user

    def test_no_user_means_no_form(self):
        newsletter.BUTTONDOWN_USER = ""
        self.assertEqual(newsletter.block("home"), "")

    def test_form_posts_straight_to_buttondown_without_script(self):
        newsletter.BUTTONDOWN_USER = "ravencrow"
        html = newsletter.block("artigo")
        self.assertIn('action="https://buttondown.com/api/emails/embed-subscribe/ravencrow"', html)
        self.assertIn('method="post"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertIn('type="email" name="email"', html)
        self.assertIn('required', html)
        self.assertIn('autocomplete="email"', html)
        self.assertIn('<label for="rc-nl-email-artigo">', html)
        self.assertNotIn("<script", html)
        self.assertNotIn("—", html)

    def test_bad_username_is_rejected(self):
        for bad in ['x"><script>', "a/b", "../x", "a b"]:
            newsletter.BUTTONDOWN_USER = bad
            with self.assertRaises(ValueError):
                newsletter.block("home")

    def test_css_is_scoped(self):
        rules = [r for r in newsletter.CSS.replace("}", "}\n").splitlines() if "{" in r and not r.startswith("@")]
        self.assertTrue(rules)
        for r in rules:
            self.assertTrue(r.lstrip().startswith(".rc-nl"), r)


class NewsletterWiringTests(unittest.TestCase):
    def test_builders_place_the_block(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        self.assertIn("newsletter_block('artigo')", (root / "build-raven.py").read_text(encoding="utf-8"))
        self.assertIn("newsletter_block('coluna')", (root / "build-column.py").read_text(encoding="utf-8"))
        self.assertIn("newsletter_block('home')", (root / "build-news-index.py").read_text(encoding="utf-8"))
        home = (root / "index.html").read_text(encoding="utf-8")
        self.assertIn("<!-- rc-newsletter:start -->", home)
        self.assertLess(home.index("<!-- rc-newsletter:end -->"), home.index('<section id="apoie"'))


if __name__ == "__main__":
    unittest.main()
