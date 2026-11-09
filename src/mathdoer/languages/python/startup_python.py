# mathdoer startup file for Python.
#
# This file runs before every prompt, in the same namespace, so everything defined here
# is available to the prompt. Edit it freely: mathdoer never overwrites your changes.
# An error in this file is reported as a startup error and the prompt is not run.

from math import *
from builtins import pow  # math.pow would otherwise turn pow(2, 100) into a float


# Defines every constant and unit from mathdoer's registry as a SCREAMING_SNAKE_CASE
# variable, for example SPEED_OF_LIGHT and INCH. A value written as a whole number
# becomes an int; any other value becomes a float. Delete this block to go without them.
def define_registry_names():
    import os
    import tomllib
    from fractions import Fraction

    with open(os.environ["MATHDOER_REGISTRY_FILE"], "rb") as registry_file:
        registry = tomllib.load(registry_file)

    for entry in registry["constants"] + registry["units"]:
        value_text = entry["value"]
        if value_text.isdigit():
            value = int(value_text)
        else:
            numerator_text, _, denominator_text = value_text.partition("/")
            value = float(Fraction(numerator_text) / Fraction(denominator_text or "1"))
        globals()[entry["name"]] = value


define_registry_names()
del define_registry_names
