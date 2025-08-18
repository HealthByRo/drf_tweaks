#! /usr/bin/env python
# This script is taken from Django Rest Framework
# (https://github.com/tomchristie/django-rest-framework/blob/master/runtests.py)
from __future__ import print_function

import os
import sys

import pytest

PYTEST_ARGS = {
    "default": ["tests", "--tb=short", "-s", "-rw"],
    "fast": ["tests", "--tb=short", "-q", "-s", "-rw"],
}

sys.path.append(os.path.dirname(__file__))


def exit_on_failure(ret, message=None):
    if ret:
        sys.exit(ret)


def split_class_and_function(string):
    class_string, function_string = string.split(".", 1)
    return "%s and %s" % (class_string, function_string)


def is_function(string):
    # `True` if it looks like a test function is included in the string.
    return string.startswith("test_") or ".test_" in string


def is_class(string):
    # `True` if first character is uppercase - assume it's a class name.
    return string[0] == string[0].upper()


if __name__ == "__main__":
    try:
        sys.argv.remove("--fast")
    except ValueError:
        style = "default"
    else:
        style = "fast"
        run_flake8 = False
        run_isort = False

    if len(sys.argv) > 1:
        pytest_args = sys.argv[1:]
        first_arg = pytest_args[0]

        try:
            pytest_args.remove("--coverage")
        except ValueError:
            pass
        else:
            pytest_args = ["--cov-report", "xml", "--cov", "drf_tweaks"] + pytest_args

        if first_arg.startswith("-"):
            # `runtests.py [flags]`
            pytest_args = ["tests"] + pytest_args
        elif is_class(first_arg) and is_function(first_arg):
            # `runtests.py TestCase.test_function [flags]`
            expression = split_class_and_function(first_arg)
            pytest_args = ["tests", "-k", expression] + pytest_args[1:]
        elif is_class(first_arg) or is_function(first_arg):
            # `runtests.py TestCase [flags]`
            # `runtests.py test_function [flags]`
            pytest_args = ["tests", "-k", pytest_args[0]] + pytest_args[1:]
    else:
        pytest_args = PYTEST_ARGS[style]

    exit_on_failure(pytest.main(pytest_args))
