from examples.calculator_plugin_base import CalculatorPluginBase


class AddPlugin(CalculatorPluginBase):

    def operation(self, x, y):
        return x + y
