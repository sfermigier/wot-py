#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jsonschema import validate

from wotpy.td.enums import InteractionTypes
from wotpy.td.jsonld.link import JsonLDLink
from wotpy.td.jsonld.schemas import interaction_schema_for_type


class JsonLDInteraction(object):
    """Wrapper class for an Interaction JSON-LD document."""

    def __init__(self, doc, validation=True):
        self._doc = doc

        if validation:
            self.validate()

    def validate(self):
        """Validates this instance agains its JSON schema."""

        validate(self._doc, interaction_schema_for_type(self.interaction_type))

    @property
    def doc(self):
        """Raw document dictionary property."""

        return self._doc

    @property
    def interaction_type(self):
        """Returns the interaction type."""

        for item in self.type:
            if item in InteractionTypes.list():
                return item

        raise ValueError("Unknown interaction type")

    @property
    def type(self):
        """Type property."""

        return self._doc.get("@type")

    @property
    def name(self):
        """Name property."""

        return self._doc.get("name")

    @property
    def output_data(self):
        """outputData property."""

        return self._doc.get("outputData")

    @property
    def input_data(self):
        """inputData property."""

        return self._doc.get("inputData")

    @property
    def writable(self):
        """Writable property."""

        return self._doc.get("writable")

    @property
    def link(self):
        """Returns a list of JsonLDLink instances that
        represent the links contained in this interaction."""

        return [JsonLDLink(item) for item in self._doc.get("link", [])]