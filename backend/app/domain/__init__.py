"""Pure domain layer.

Domain code must not perform I/O, read the clock, read environment/configuration, or touch the
database. Inputs (including ``as_of_date`` and the ruleset) are passed in explicitly.
``tests/unit/test_clock.py`` enforces the clock rule by static inspection.
"""
