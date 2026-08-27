from configparser import ConfigParser

from packaging.version import Version

# Defaults used for any [Documentation] field a plugin's info file doesn't specify.
_DOCUMENTATION_DEFAULTS = {
    "Author": "Unknown",
    "Version": "0.0",
    "Website": "None",
    "Copyright": "Unknown",
    "Description": "",
}


class Plugin:
    """
    Represents a single plugin: the metadata parsed from its info file (name, version, author,
    copyright, website, description) plus, once PluginManager has instantiated it, the
    plugin_object itself.

    Metadata is backed by a configparser.ConfigParser (see `details`). Values are read with a
    fallback, so a plugin's info file only needs to specify what it wants to override -- the
    fallback values themselves are never written back into `details`, so `details` reflects
    only what was actually parsed from the info file (plus whatever `name`/`path`/etc. setters
    have explicitly been called with).
    """

    def __init__(self, plugin_name, plugin_path):
        # Used as the fallback for name/path if `details` doesn't specify Core/Name or
        # Core/Module -- see __read().
        self.__default_name = plugin_name
        self.__default_path = plugin_path
        self.__details = ConfigParser()

        # Set by PluginManager once the plugin's module class has been instantiated; None until then.
        self.plugin_object = None

    def __read(self, section: str, option: str, default: str) -> str:
        return self.__details.get(section, option, fallback=default)

    def __write(self, section: str, option: str, value: str) -> None:
        if not self.__details.has_section(section):
            self.__details.add_section(section)
        self.__details.set(section, option, value)

    @property
    def details(self) -> ConfigParser:
        return self.__details

    @details.setter
    def details(self, config_details: ConfigParser) -> None:
        self.__details = config_details

    @property
    def name(self):
        return self.__read("Core", "Name", self.__default_name)

    @name.setter
    def name(self, name):
        self.__write("Core", "Name", name)

    @property
    def path(self):
        return self.__read("Core", "Module", self.__default_path)

    @path.setter
    def path(self, path):
        self.__write("Core", "Module", path)

    @property
    def version(self):
        return Version(self.__read("Documentation", "Version", _DOCUMENTATION_DEFAULTS["Version"]))

    @version.setter
    def version(self, ver):
        if isinstance(ver, Version):
            ver = str(ver)
        self.__write("Documentation", "Version", ver)

    @property
    def author(self):
        return self.__read("Documentation", "Author", _DOCUMENTATION_DEFAULTS["Author"])

    @author.setter
    def author(self, author):
        self.__write("Documentation", "Author", author)

    @property
    def copyright(self):
        return self.__read("Documentation", "Copyright", _DOCUMENTATION_DEFAULTS["Copyright"])

    @copyright.setter
    def copyright(self, copyright):
        self.__write("Documentation", "Copyright", copyright)

    @property
    def website(self):
        return self.__read("Documentation", "Website", _DOCUMENTATION_DEFAULTS["Website"])

    @website.setter
    def website(self, website):
        self.__write("Documentation", "Website", website)

    @property
    def description(self):
        return self.__read("Documentation", "Description", _DOCUMENTATION_DEFAULTS["Description"])

    @description.setter
    def description(self, description):
        self.__write("Documentation", "Description", description)
