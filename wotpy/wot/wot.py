#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rx import Observable


class DiscoveryType(object):
    """Enumeration of discovery types."""

    ANY = 'any'
    LOCAL = 'local'
    NEARBY = 'nearby'
    DIRECTORY = 'directory'
    BROADCAST = 'broadcast'
    OTHER = 'other'

    @classmethod
    def list(cls):
        """Returns a list with all discovery types."""

        return [
            cls.ANY, cls.LOCAL, cls.NEARBY,
            cls.DIRECTORY, cls.BROADCAST, cls.OTHER
        ]


class ThingFilter(object):
    """Represents a filter that may be applied
    to a things discovery operation."""

    def __init__(self, url, description, method=DiscoveryType.ANY):
        assert method in DiscoveryType.list()
        self.discovery_type = method
        self.url = url
        self.description = description


class ThingInit(object):
    """Represents the set of properties required
    to create a locally hosted thing."""

    def __init__(self, name, url, description=None):
        """Constructor. If description is None a basic empty
        thing description document will be used instead."""

        self.name = name
        self.url = url
        self.description = description if description else {'name': self.name}


class WoT(object):
    """WoT entrypoint."""

    def __init__(self, servient):
        self.servient = servient

    def discover(self, thing_filter):
        """Takes a ThingFilter instance and returns an Observable
        that will emit events for each discovered Thing or error."""

        # noinspection PyUnresolvedReferences
        return Observable.empty()

    def consume(self, url):
        """Takes a URL and returns a Future that resolves to a
        ConsumedThing that has been retrieved from the given URL."""

        pass

    def expose(self, thing_init):
        """Takes a ThingInit instance and returns a Future that resolves
        to an ExposedThing that will be hosted in the local servient."""

        pass
