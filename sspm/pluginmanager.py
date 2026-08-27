import importlib.util
import inspect
import logging
import pathlib
import sys
from configparser import ConfigParser

from .plugin import Plugin


class PluginManager:
    """
    A basic python plugin manager. Plugins live one per subdirectory of a user-specified plugin
    folder, each with a Python module and an info file (see plugin.py) describing it.
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

    def import_plugins(self) -> None:
        """
        Imports all plugins in the user-defined plugin directory. Each subdirectory containing a matching
        plugin info file is expected to hold exactly one module defining exactly one PluginBase subclass;
        plugins that don't meet that contract, or whose module can't be found, are skipped and logged
        rather than raised.
        """
        for plugin_info_path in pathlib.Path(self.__plugin_folder).glob(f"**/*.{self.__plugin_config_ext}"):
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
                                continue

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

    def __categorize_plugin(self, plugin) -> None:
        """
        Indexes a plugin under the name of each base class its plugin_object directly subclasses, so it can
        later be looked up by category via categorized_plugins.
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
        return self.__imported_plugins.get(plugin_name)

    def remove_plugin(self, plugin_name) -> None:
        """
        Removes a loaded plugin.
        :param plugin_name: the name of the plugin to be removed
        :return: None
        :raises KeyError: if no plugin with that name is currently active.
        """
        del self.__imported_plugins[plugin_name]
        self.__logging.info(f"{plugin_name} removed successfully.")

    @property
    def active_plugins(self):
        """A dict of all successfully imported plugins, keyed by plugin name."""
        return self.__imported_plugins

    @property
    def categorized_plugins(self):
        """
        A dict mapping each PluginBase subclass name to a dict of the plugins (keyed by plugin name)
        whose plugin_object directly subclasses it.
        """
        return self.__categorized_plugins
