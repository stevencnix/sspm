from sspm import PluginBase


class FirstPlugin(PluginBase):
    """One of two PluginBase subclasses in this module, for
    test_module_with_multiple_plugin_classes_is_skipped."""
    pass


class SecondPlugin(PluginBase):
    """The other of the two."""
    pass
