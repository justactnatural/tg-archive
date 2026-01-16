import os
import tempfile
import unittest

try:
    import yaml  # noqa: F401
except Exception as e:  # pragma: no cover
    raise unittest.SkipTest("missing dependencies: {}".format(e))

from tgarchive.__init__ import get_config


class ConfigTests(unittest.TestCase):
    def test_group_defaults_merge(self):
        cfg = {
            "defaults": {
                "api_id": "1",
                "api_hash": "2",
                "download_media": True,
                "message_ids": [1, 2],
                "author_ids": [9],
            },
            "groups": [
                {"name": "A", "group": "group-a"},
                {"name": "B", "group": "group-b", "download_media": False},
            ],
            "build": {
                "publish_dir": "site",
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            with open(path, "w", encoding="utf8") as f:
                f.write(yaml.safe_dump(cfg))

            config = get_config(path)
            self.assertEqual(len(config["groups"]), 2)
            self.assertTrue(config["groups"][0]["download_media"])
            self.assertFalse(config["groups"][1]["download_media"])
            self.assertEqual(config["groups"][0]["data"], "data/group-a.sqlite")
            self.assertEqual(config["groups"][0]["message_ids"], [1, 2])
            self.assertEqual(config["groups"][0]["author_ids"], [9])


if __name__ == "__main__":
    unittest.main()
