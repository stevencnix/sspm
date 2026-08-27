from pathlib import Path

from sspm.pluginmanager import PluginManager

if __name__ == "__main__":
    path = Path("./plugins").resolve().as_posix()
    plugin_manager = PluginManager("./plugins")
    plugin_manager.import_plugins()

    # To see all loaded plugins you can use active_plugins
    print("Showing Loaded Plugins:")
    for plugin_name in plugin_manager.active_plugins.keys():
        print(f"loaded plugin: {plugin_name}")
    print("\n")

    # The plugin manager also supports plugin categories, letting you get plugins grouped by the
    # PluginBase subclass they use. Here, Add and Subtract are both in the CalculatorPluginBase
    # category since both plugins subclass CalculatorPluginBase.
    print("Showing Calculator Operation Plugins")
    operation_plugins = plugin_manager.categorized_plugins.get("CalculatorPluginBase")
    for plugin_name in operation_plugins.keys():
        print(f"loaded operations: {plugin_name}")
    print("\n")

    # Use the plugin name provided in the info file. This returns a Plugin, which holds the metadata
    # from the info file plus plugin_object -- the actual instantiated object with the plugin's
    # functionality.
    print("Showing Add functionality")
    add_plugin = plugin_manager.get_active_plugin("Add Plugin")
    add_operation = add_plugin.plugin_object
    value = add_operation.operation(1, 2)
    print(f"added 1 and 2: {value}")
    print("\n")

    print("Showing Subtract functionality")
    subtract_plugin = plugin_manager.get_active_plugin("Subtract Plugin")
    subtract_operation = subtract_plugin.plugin_object
    value = subtract_operation.operation(1, 2)
    print(f"subtracted 1 and 2: {value}")
