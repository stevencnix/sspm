# Super Simple Plugin Manager - SSPM

## About SSPM

Super Simple Plugin Manager - SSPM is a lightweight, hands-off Python plugin manager. Drop a
plugin's code and a small `.info` file describing it into a plugins directory, and SSPM discovers,
imports, categorizes, and instantiates it for you — no extra registration step needed.

## Requirements

- Python 3.8+
- [packaging](https://pypi.org/project/packaging/) (installed automatically as a dependency)

## Installation

The easiest way to install is to use pip:

    pip install SSPM

or if you have cloned the repo:

    cd <path to repo>
    pip install .

## Writing a Plugin

A plugin is a folder containing two files: a Python module with your plugin's code, and an `.info` file
(a standard `configparser`/INI file) describing it. Each module must define **exactly one** class that
subclasses `PluginBase` (or a subclass of it) — SSPM uses that to find and categorize your plugin.

```
plugins/
└── add_plugin/
    ├── add_plugin.py
    └── add.info
```

`add_plugin.py`:

```python
from sspm import PluginBase


class AddPlugin(PluginBase):

    def operation(self, x, y):
        return x + y
```

`add.info`:

```ini
[Core]
Name = Add Plugin
Module = add_plugin

[Documentation]
Author = Your Name
Version = 1.0.0
Website = None
Description = Plugin performing basic add operation
```

`Core.Name` and `Core.Module` are required (`Module` is the module filename, without the `.py`
extension). Everything under `[Documentation]` is optional — SSPM fills in sensible defaults
(`Unknown`, `0.0`, etc.) for anything you leave out.

You can subclass `PluginBase` further to create your own plugin categories (e.g. a
`CalculatorPluginBase`) and group related plugins together — see
[`examples/`](examples) for a full working example with multiple plugin types.

## Basic Usage

1. Initialize the plugin manager, pointing it at the folder containing your plugins:

    ```python
    from sspm import PluginManager

    plugin_manager = PluginManager(plugin_folder="./plugins")
    ```

2. Import the plugins in the plugins directory:

    ```python
    plugin_manager.import_plugins()
    ```

3. Get a specific imported plugin by the name from its `.info` file:

    ```python
    plugin = plugin_manager.get_active_plugin("Add Plugin")
    result = plugin.plugin_object.operation(1, 2)
    ```

    or get all active plugins:

    ```python
    plugins = plugin_manager.active_plugins
    ```

    or get plugins grouped by their `PluginBase` category:

    ```python
    calculator_plugins = plugin_manager.categorized_plugins.get("CalculatorPluginBase")
    ```

A `Plugin` object exposes the metadata from its `.info` file (`name`, `version`, `author`,
`website`, `copyright`, `description`) as well as `plugin_object`, the instantiated plugin class
itself.

## More Examples

See the [`examples/`](examples) directory for a runnable calculator example with `Add` and
`Subtract` plugins, and [`CHANGELOG`](CHANGELOG) for release history.

## License

SSPM is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE) — free to use, modify,
and distribute for any noncommercial purpose. Commercial use requires a separate license from the
author.
