#!/usr/bin/env python3
"""
This is a demo test file to illustrate how to write unit tests for a Python package.
It serves as an example for educational purposes only.
"""

import unittest

from athletics_performance.athletics_performance import example_function


# TODO: the following testing functions are placeholders: you need to update the tests so that
# the function calls and expected_result are correct.
class TestAthleticsPerformance(unittest.TestCase):
    def test_example_function(
        self,
    ):
        res = example_function()
        expected_result = "Hello from athletics_performance.athletics_performance !"
        assert res == expected_result
