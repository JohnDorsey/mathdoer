"""Helpers for tests that need interface settings of every kind."""
from mathdoer.interface_settings import SETTING_DESCRIPTIONS, InterfaceSettings


def random_settings(generator):
    """Interface settings with every yes-or-no setting and every number chosen at random."""
    values = {}
    for description in SETTING_DESCRIPTIONS:
        if description.value_type is bool:
            values[description.name] = generator.choice([True, False])
        else:
            values[description.name] = generator.randint(description.minimum, description.maximum)
    return InterfaceSettings(**values)


def every_feature_off():
    """Interface settings with every yes-or-no setting off: a plain text editor."""
    return InterfaceSettings(
        **{description.name: False for description in SETTING_DESCRIPTIONS if description.value_type is bool}
    )
