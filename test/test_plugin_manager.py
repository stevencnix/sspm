import pathlib
import unittest

from sspm import PluginManager

# Resolved relative to this file so the suite behaves the same regardless of the
# working directory it's invoked from (e.g. `cd test && python -m unittest ...`
# vs. `python -m unittest discover` from the repo root).
TEST_PLUGINS_DIR = pathlib.Path(__file__).resolve().parent / "test_files" / "plugins"


class TestPluginManager(unittest.TestCase):

    def setUp(self) -> None:
        self.plugin_manager = PluginManager(str(TEST_PLUGINS_DIR))
        self.plugin_manager.import_plugins()

    def test_plugin_manager(self):
        self.assertIsNotNone(self.plugin_manager)

    def test_plugin_import(self):
        self.assertEqual({"Add Plugin", "Subtract Plugin"}, set(self.plugin_manager.active_plugins.keys()))

    def test_plugin_operation(self):
        add_plugin = self.plugin_manager.get_active_plugin("Add Plugin")
        self.assertEqual(3, add_plugin.plugin_object.operation(1, 2))

    def test_categorized_plugins(self):
        calculator_plugins = self.plugin_manager.categorized_plugins.get("CalculatorPluginBase")
        self.assertEqual({"Add Plugin", "Subtract Plugin"}, set(calculator_plugins.keys()))


suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManager)
])
