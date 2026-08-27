Installation
============

The easiest way to install is to use pip::

    pip install SSPM

or if you have cloned the repo::

    cd <path to repo>
    pip install .

Basic Usage
-----------

1. Initialize the plugin manager, pointing it at the folder containing your plugins:

.. code-block:: python

    from sspm import PluginManager

    plugin_manager = PluginManager(plugin_folder="./plugins")

2. Import the plugins in the plugins directory:

.. code-block:: python

    plugin_manager.import_plugins()

3. Get the imported plugin:

.. code-block:: python

    plugin = plugin_manager.get_active_plugin("Plugin name")

   or get all active plugins:

.. code-block:: python

    plugins = plugin_manager.active_plugins
