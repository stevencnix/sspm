from sspm import PluginBase


class NoDocumentationPlugin(PluginBase):
    """A valid, otherwise-normal plugin whose .info file has no [Documentation] section at all."""
    pass
