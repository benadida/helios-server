"""
This django app is meant only to connect the pieces of Helios and Auth that are specific to Votwee
"""

import glue

import helios

helios.TEMPLATE_BASE = "votwee/templates/base.html"