import unittest

from . import test_examples, test_plugin_manager

MainTestSuite = unittest.TestSuite(
    [  # add the tests suites below
        test_plugin_manager.suite,
        test_examples.suite,
    ])
