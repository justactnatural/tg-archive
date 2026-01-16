import unittest

try:
    import yaml  # noqa: F401
    import telethon  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.sync import Sync


class SyncAuthorTests(unittest.TestCase):
    def test_normalize_username(self):
        s = Sync.__new__(Sync)
        self.assertEqual(s._normalize_username("@UserName"), "username")

    def test_resolve_author_ids_by_username(self):
        s = Sync.__new__(Sync)
        resolved = s._resolve_author_ids([], ["@alice"], resolve_func=lambda _: 42)
        self.assertEqual(resolved, [42])

    def test_resolve_author_ids_missing(self):
        s = Sync.__new__(Sync)
        with self.assertRaises(ValueError):
            s._resolve_author_ids([], ["missing"], resolve_func=lambda _: (_ for _ in ()).throw(Exception("nope")))

    def test_should_include_author(self):
        s = Sync.__new__(Sync)
        s.allowed_author_ids = {7}
        self.assertTrue(s._should_include_author(7))
        self.assertFalse(s._should_include_author(8))
        self.assertFalse(s._should_include_author(None))


if __name__ == "__main__":
    unittest.main()
