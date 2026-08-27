import pathlib
import tempfile
import threading
import time
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


def _write_plugin(plugins_dir: pathlib.Path, module_name: str, class_name: str) -> None:
    plugin_dir = plugins_dir / module_name
    plugin_dir.mkdir()
    (plugin_dir / f"{module_name}.py").write_text(
        f"from sspm import PluginBase\n\n\nclass {class_name}(PluginBase):\n    pass\n"
    )
    (plugin_dir / f"{module_name}.info").write_text(f"[Core]\nName = {class_name}\nModule = {module_name}\n")


class TestPluginManagerRescan(unittest.TestCase):
    """
    rescan() is meant for picking up plugins added to the plugin directory after the initial
    import_plugins() call, while the process is still running -- without disturbing plugins
    that are already active.
    """

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.plugins_dir = pathlib.Path(self._tmpdir.name)
        _write_plugin(self.plugins_dir, "first_plugin", "FirstPlugin")

    def test_rescan_picks_up_a_plugin_added_after_the_initial_scan(self):
        plugin_manager = PluginManager(str(self.plugins_dir))
        plugin_manager.import_plugins()
        self.assertEqual({"FirstPlugin"}, set(plugin_manager.active_plugins.keys()))

        _write_plugin(self.plugins_dir, "second_plugin", "SecondPlugin")
        plugin_manager.rescan()

        self.assertEqual({"FirstPlugin", "SecondPlugin"}, set(plugin_manager.active_plugins.keys()))

    def test_rescan_does_not_reinstantiate_an_already_active_plugin(self):
        plugin_manager = PluginManager(str(self.plugins_dir))
        plugin_manager.import_plugins()
        original_plugin_object = plugin_manager.get_active_plugin("FirstPlugin").plugin_object

        _write_plugin(self.plugins_dir, "second_plugin", "SecondPlugin")
        plugin_manager.rescan()

        self.assertIs(original_plugin_object, plugin_manager.get_active_plugin("FirstPlugin").plugin_object)


class TestPluginManagerThreadSafety(unittest.TestCase):
    """
    Hammers a single PluginManager with one thread growing active_plugins/categorized_plugins
    (via rescan() picking up newly-added plugins) while several others continuously iterate
    snapshots of them. This specifically needs the *dict* to change size while another thread
    holds a reference into it to have any chance of tripping "dictionary changed size during
    iteration" -- re-importing the same fixed set of plugins over and over (as import_plugins()
    does on repeat calls) never changes dict size and can't exercise this, no matter how many
    threads or iterations are thrown at it.

    Caveat, found the hard way while writing this: on the CPython build this was developed
    against, this test could not be made to fail even with the locking removed entirely (tried a
    naive busy loop, a version with time.sleep(0) yields, up to 200 plugins and 8 readers, and
    sys.setswitchinterval(0.00001) to force much more frequent GIL switches -- none reproduced a
    crash or an observable active_plugins/categorized_plugins inconsistency). That's evidence the
    race window here is narrow on this interpreter, not proof the race doesn't exist -- dict
    mutation isn't guaranteed atomic across arbitrary Python versions/implementations, and
    import_plugins()/rescan() update two separate dicts (__imported_plugins then
    __categorized_plugins) as two distinct statements, which is exactly the shape of bug a lock is
    supposed to guard against even when it's hard to force in practice. So: treat this as a smoke
    test for "doesn't crash and ends up in a consistent final state" rather than as proof the
    locking is load-bearing -- it wasn't able to demonstrate that either way.
    """

    def test_concurrent_rescan_and_reads_do_not_crash(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        plugins_dir = pathlib.Path(tmpdir.name)
        plugin_manager = PluginManager(str(plugins_dir))
        errors = []
        stop = threading.Event()

        def grow():
            try:
                for i in range(40):
                    _write_plugin(plugins_dir, f"plugin_{i}", f"Plugin{i}")
                    plugin_manager.rescan()
            except Exception as e:
                errors.append(e)
            finally:
                # Must always fire, even on failure above -- otherwise the reader threads' "while
                # not stop.is_set()" loops never end and the whole test hangs instead of failing.
                stop.set()

        def read_continuously():
            try:
                while not stop.is_set():
                    list(plugin_manager.active_plugins.items())
                    list(plugin_manager.categorized_plugins.items())
                    # A bare busy-loop here starves the writer thread of the GIL badly enough
                    # (confirmed: the writer barely made progress in 15s against 2 such readers)
                    # that the test just looks hung, regardless of locking correctness. Yielding
                    # keeps this a real concurrency test instead of a GIL-contention test.
                    time.sleep(0)
            except Exception as e:
                errors.append(e)

        writer = threading.Thread(target=grow, daemon=True)
        readers = [threading.Thread(target=read_continuously, daemon=True) for _ in range(8)]
        writer.start()
        for t in readers:
            t.start()
        writer.join(timeout=60)
        stop.set()  # in case the writer itself hung rather than raised, so readers still exit
        for t in readers:
            t.join(timeout=60)

        self.assertFalse(writer.is_alive(), "writer thread did not finish -- see errors below")
        self.assertFalse(any(t.is_alive() for t in readers), "a reader thread did not finish")
        self.assertEqual([], errors)
        self.assertEqual(40, len(plugin_manager.active_plugins))


suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManager),
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManagerEdgeCases),
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManagerRescan),
    unittest.TestLoader().loadTestsFromTestCase(TestPluginManagerThreadSafety),
])
