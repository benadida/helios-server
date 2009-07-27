"""
This django app is meant only to connect the pieces of Helios and Auth that are specific to IACR
"""

import glue

import helios

helios.TEMPLATE_BASE = "iacr/templates/base.html"