from examples.calculator_plugin_base import CalculatorPluginBase


class SubtractPlugin(CalculatorPluginBase):

    def operation(self, x, y):
        return x - y
