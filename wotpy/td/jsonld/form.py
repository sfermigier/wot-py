#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jsonschema import validate

from wotpy.td.jsonld.schemas import SCHEMA_FORM


class JsonLDForm(object):
    """Wrapper class for a Form document serialized in JSON-LD."""

    def __init__(self, doc, jsonld_interaction):
        self._doc = doc
        self.jsonld_interaction = jsonld_interaction
        self.validate()

    def validate(self):
        """Validates this instance agains its JSON schema."""

        validate(self._doc, SCHEMA_FORM)

    @property
    def doc(self):
        """Raw document dictionary property."""

        return self._doc

    @property
    def href(self):
        """URI of the endpoint where an interaction pattern is provided."""

        return self._doc.get("href")

    @property
    def media_type(self):
        """Underlying media type of the interaction form."""

        return self._doc.get("mediaType")

    @property
    def rel(self):
        """Indicates the expected result of performing the operation described by the form."""

        return self._doc.get("rel")

    @property
    def metadata(self):
        """Returns a dict containing the metadata for this thing description.
        This is, all fields that are not part of the expected set."""

        base_keys = list(SCHEMA_FORM["properties"].keys())
        meta_keys = [key for key in list(self._doc.keys()) if key not in base_keys]

        return {key: self._doc[key] for key in meta_keys}
