#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse, urlunparse
except ImportError:
    # noinspection PyCompatibility
    from urlparse import urlparse, urlunparse

from jsonschema import validate, ValidationError

from wotpy.td.jsonld.interaction import JsonLDInteraction
from wotpy.td.jsonld.schemas import SCHEMA_THING_DESCRIPTION
from wotpy.td.constants import WOT_CONTEXT_URL


class JsonLDThingDescription(object):
    """Wrapper class for a Thing Description JSON-LD document."""

    def __init__(self, doc, validation=True):
        self._doc = doc

        if validation:
            self.validate()

    def _validate_context(self):
        """Raises a JSON schema validation error if this document lacks the required context."""

        parsed_context_url = urlparse(WOT_CONTEXT_URL)

        parts_http = ["http"] + list(parsed_context_url[1:])
        parts_https = ["https"] + list(parsed_context_url[1:])

        valid_urls = [
            urlunparse(parts_http),
            urlunparse(parts_https)
        ]

        try:
            next(item for item in valid_urls if item in self.context)
        except StopIteration:
            raise ValidationError("Missing context: {}".format(WOT_CONTEXT_URL))

    def validate(self):
        """Validates this instance agains its JSON schema."""

        validate(self._doc, SCHEMA_THING_DESCRIPTION)
        self._validate_context()

    @property
    def doc(self):
        """Raw document dictionary property."""

        return self._doc

    @property
    def name(self):
        """Name property."""

        return self._doc.get("name")

    @property
    def base(self):
        """Base property."""

        return self._doc.get("base")

    @property
    def type(self):
        """Type property."""

        return self._doc.get("@type")

    @property
    def context(self):
        """Context property."""

        return self._doc.get("@context")

    @property
    def interaction(self):
        """Returns a list of JsonLDInteraction instances that represent
        the interactions contained in this Thing Description."""

        return [JsonLDInteraction(item) for item in self._doc.get("interaction", [])]