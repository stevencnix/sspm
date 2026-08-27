from abc import ABC, abstractmethod

from sspm.plugin_base import PluginBase


class CalculatorPluginBase(ABC, PluginBase):
    """A PluginBase category for two-operand arithmetic operations, e.g. add/subtract plugins."""

    @abstractmethod
    def operation(self, x, y):
        """Apply this plugin's operation to x and y and return the result."""