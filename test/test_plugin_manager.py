import pathlib
import unittest

from packaging.version import Version

from sspm import PluginManager

# Resolved relative to this file so the suite behaves the same regardless of the
# working directory it's invoked from (e.g. `cd test && python -m unittest ...`
# vs. `python -m unittest discover` from the repo root).
TEST_PLUGINS_DIR = pathlib.Path(__file__).resolve().parent / "test_files" / "plugins"
EDGE_CASE_PLUGINS_DIR = pathlib.Path(__file__).resolve().parent / "test_files" / "edge_case_plugins"


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


class TestPluginManagerEdgeCases(unittest.TestCase):
    """
    Regression tests for import_plugins()'s handling of malformed plugins. Each of these used to
    either crash the entire scan or silently misbehave rather than being skipped and logged.
    """

    def setUp(self) -> None:
        self.plugin_manager = PluginManager(str(EDGE_CASE_PLUGINS_DIR))
        self.plugin_manager.import_plugins()

    def test_module_with_zero_plugin_classes_is_skipped(self):
        # Used to raise an unhandled IndexError (cls_name[0] on an empty list), aborting the
        # entire scan rather than just skipping this one plugin.
        self.assertNotIn("No Plugin Class", self.plugin_manager.active_plugins)

    def test_module_with_multiple_plugin_classes_is_skipped(self):
        # Used to log an error but still register a broken Plugin with plugin_object left as
        # None, rather than skipping it outright.
        self.assertNotIn("Multi Plugin Class", self.plugin_manager.active_plugins)

    def test_plugin_missing_documentation_section_gets_defaults(self):
        # Used to crash with configparser.NoSectionError, since ConfigParser.has_option raises
        # that when the section itself (not just the option) is missing.
        plugin = self.plugin_manager.get_active_plugin("No Documentation")
        self.assertIsNotNone(plugin)
        self.assertEqual("Unknown", plugin.author)
        self.assertEqual(Version("0.0"), plugin.version)
        self.assertEqual("None", plugin.website)
        self.assertEqual("Unknown", plugin.copyright)
        self.assertEqual("", plugin.description)

    def test_valid_plugin_still_loads_alongside_malformed_siblings(self):
        # A malformed plugin elsewhere in the directory shouldn't prevent a valid plugin in the
        # same scan from loading.
        self.assertIn("No Documentation", self.plugin_manager.active_plugins)


suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManager),
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManagerEdgeCases),
])
