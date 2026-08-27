import importlib.util
import inspect
import logging
import pathlib
import sys
import threading
from configparser import ConfigParser

from .plugin import Plugin


class PluginManager:
    """
    A basic python plugin manager. Plugins live one per subdirectory of a user-specified plugin
    folder, each with a Python module and an info file (see plugin.py) describing it.

    Safe to use from multiple threads: all reads and mutations of the manager's internal plugin
    state (import_plugins, rescan, remove_plugin, get_active_plugin, active_plugins,
    categorized_plugins) are serialized with an internal lock, and active_plugins/
    categorized_plugins return snapshots rather than live references, so a caller iterating one
    won't be affected by a concurrent import_plugins()/rescan()/remove_plugin() call.
    """

    def __init__(self, plugin_folder: str, plugin_info_ext="info", log=logging):
        """
        This is the initialization method. User must set the plugin folder location. They can also set their own
        logging should they have their own.
        :param plugin_folder: Base dir for plugins.
        :param plugin_info_ext: Allows user to define a custom extension for their plugin info files.
        :param log: Python logging.
        """
        self.__logging = log
        self.__plugin_folder = pathlib.Path(plugin_folder)
        self.__plugin_config_ext = plugin_info_ext
        self.__imported_plugins = dict()
        self.__categorized_plugins = dict()
        self.__lock = threading.Lock()

    # Follows the recipe in the Python docs for importing a source file directly:
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    # This is a better and more flexible solution than the python path modification. This also allows for
    # subdirectories within the provided plugin directory.
    def __load_plugin_src(self, name: str, plugin_path: str):
        """
        Import a Python source file and return the loaded module.

        :param name: The name for the loaded module. It may contain `.` and even characters
            that would normally not be allowed (e.g., `-`).
        :param plugin_path: The full path to the source file. It may contain characters like
            `.` or `-`.
        :return: The imported module.
        :raises ImportError: If the file cannot be imported (e.g., if it's not a `.py` file or
            if it does not exist).
        :raises Exception: Any exception that is raised while executing the module (e.g., a
            `SyntaxError`). These are errors made by the author of the module!
        """
        spec = importlib.util.spec_from_file_location(name, plugin_path)
        if spec is None:
            raise ImportError(f"Could not load spec for module '{name}' at: {plugin_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except FileNotFoundError as e:
            raise ImportError(f"{e.strerror}: {plugin_path}") from e
        return module

    def __import_plugin_info(self, plugin_info_path: pathlib.Path) -> None:
        """
        Loads a single plugin from its info file and, if successful, registers it. Shared by
        import_plugins() and rescan(); callers are expected to hold self.__lock.
        """
        config_parser = ConfigParser()
        config_parser.read(plugin_info_path)
        try:
            if config_parser.get("Core", "Module"):
                module_name = config_parser.get("Core", "Module")
                module_parent_dir = plugin_info_path.parent
                module_path = module_parent_dir.joinpath(f"{module_name}.py").resolve().as_posix()
                importlib.invalidate_caches()
                module = self.__load_plugin_src(module_name, module_path)
                if module:
                    if config_parser.get("Core", "Name"):
                        plugin = Plugin(config_parser.get("Core", "Name"), module_path)
                        plugin.details = config_parser

                        cls_names = [m[0] for m in inspect.getmembers(module, inspect.isclass) if
                                     m[1].__module__ == module.__name__]

                        cls_name = [cls for cls in cls_names
                                    if "PluginBase" in [x.__name__ for x in type.mro(getattr(module, cls))]]

                        if cls_name.__len__() != 1:
                            self.__logging.error(
                                f"Illegal action: expected exactly one plugin class in module. "
                                f"The plugin file: {module_name} contains {len(cls_name)} plugin classes.")
                            return

                        _cls = getattr(module, cls_name[0])
                        plugin.plugin_object = _cls()

                        self.__imported_plugins[plugin.name] = plugin
                        self.__categorize_plugin(plugin)

                        self.__logging.info(f"{plugin.name} imported successfully.")
                else:
                    self.__logging.warning(f"Missing Module for Plugin: {plugin_info_path.absolute().as_posix()}")
            else:
                raise ValueError("Plugin Config file is missing necessary parameters.")
        except ModuleNotFoundError:
            self.__logging.warning(f"Missing Module for Plugin: {plugin_info_path.absolute().as_posix()}")

    def import_plugins(self) -> None:
        """
        Imports all plugins in the user-defined plugin directory. Each subdirectory containing a matching
        plugin info file is expected to hold exactly one module defining exactly one PluginBase subclass;
        plugins that don't meet that contract, or whose module can't be found, are skipped and logged
        rather than raised.

        Every matching plugin is (re)imported and its plugin_object (re)instantiated, even ones
        already active from a previous call -- to pick up only newly-added plugins without
        disturbing already-loaded ones, use rescan() instead.
        """
        with self.__lock:
            for plugin_info_path in pathlib.Path(self.__plugin_folder).glob(f"**/*.{self.__plugin_config_ext}"):
                self.__import_plugin_info(plugin_info_path)

    def rescan(self) -> None:
        """
        Scans the plugin directory for plugins that aren't already active and imports those,
        leaving already-active plugins (matched by the Name in their info file) untouched -- their
        existing plugin_object is not re-instantiated or replaced. Use this to pick up plugins
        dropped into the plugin directory after the initial import_plugins() call, while the
        process is still running.
        """
        with self.__lock:
            for plugin_info_path in pathlib.Path(self.__plugin_folder).glob(f"**/*.{self.__plugin_config_ext}"):
                config_parser = ConfigParser()
                config_parser.read(plugin_info_path)
                name = config_parser.get("Core", "Name", fallback=None)
                if name is not None and name in self.__imported_plugins:
                    continue
                self.__import_plugin_info(plugin_info_path)

    def __categorize_plugin(self, plugin) -> None:
        """
        Indexes a plugin under the name of each base class its plugin_object directly subclasses, so it can
        later be looked up by category via categorized_plugins. Callers are expected to hold self.__lock.
        :param plugin: The Plugin to index.
        """
        plugin_types = [x.__name__ for x in type(plugin.plugin_object).__bases__]

        for plugin_type in plugin_types:
            if plugin_type not in self.__categorized_plugins:
                self.__categorized_plugins[plugin_type] = {plugin.name: plugin}
            else:
                plugins_store = self.__categorized_plugins.get(plugin_type)
                plugins_store[plugin.name] = plugin

    def get_active_plugin(self, plugin_name: str) -> Plugin:
        """
        Retrieves a plugin from the active plugins.
        :param plugin_name: User defined name of plugin from plugin info file
        :return: The matching Plugin, or None if no plugin with that name is active.
        """
        with self.__lock:
            return self.__imported_plugins.get(plugin_name)

    def remove_plugin(self, plugin_name) -> None:
        """
        Removes a loaded plugin.
        :param plugin_name: the name of the plugin to be removed
        :return: None
        :raises KeyError: if no plugin with that name is currently active.
        """
        with self.__lock:
            del self.__imported_plugins[plugin_name]
            self.__logging.info(f"{plugin_name} removed successfully.")

    @property
    def active_plugins(self):
        """A snapshot dict of all successfully imported plugins, keyed by plugin name."""
        with self.__lock:
            return dict(self.__imported_plugins)

    @property
    def categorized_plugins(self):
        """
        A snapshot dict mapping each PluginBase subclass name to a dict of the plugins (keyed by
        plugin name) whose plugin_object directly subclasses it.
        """
        with self.__lock:
            return {plugin_type: dict(plugins) for plugin_type, plugins in self.__categorized_plugins.items()}
