#!/usr/bin/env python
# -*- coding: utf-8 -*-

from wotpy.wot.enums import DiscoveryMethod, TDChangeType, TDChangeMethod


class ThingFilter(object):
    """Represents a filter that may be applied
    to a things discovery operation."""

    def __init__(self, url, description, method=DiscoveryMethod.ANY):
        assert method in DiscoveryMethod.list()
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
        self.description = description if description else {"name": self.name}


class SemanticType(object):
    """Represents a semantic type annotation, containing a name and a context."""

    def __init__(self, name, context):
        self.name = name
        self.context = context


class ThingPropertyInit(object):
    """Represents the set of properties required to initialize a thing property."""

    def __init__(self, name, value, configurable=False, enumerable=True,
                 writable=True, semantic_types=None, description=None):
        self.name = name
        self.value = value
        self.configurable = configurable
        self.enumerable = enumerable
        self.writable = writable
        self.semantic_types = semantic_types
        self.description = description


class ThingEventInit(object):
    """Represents the set of properties required to initialize a thing event."""

    def __init__(self, name, semantic_types=None, data_description=None):
        self.name = name
        self.semantic_types = semantic_types
        self.data_description = data_description


class ThingActionInit(object):
    """Represents the set of properties required to initialize a thing action."""

    def __init__(self, name, action, input_data_description=None,
                 output_data_description=None, semantic_types=None):
        self.name = name
        self.action = action
        self.input_data_description = input_data_description
        self.output_data_description = output_data_description
        self.semantic_types = semantic_types


class PropertyChangeEventInit(object):
    """Represents a change Property."""

    def __init__(self, name, value):
        self.name = name
        self.value = value


class ActionInvocationEventInit(object):
    """Represents the notification data from the Action invocation."""

    def __init__(self, action_name, return_value):
        self.action_name = action_name
        self.return_value = return_value


class ThingDescriptionChangeEventInit(object):
    """The data attribute represents the changes that occurred to the Thing Description."""

    def __init__(self, td_change_type, method, name, data, description):
        assert td_change_type in TDChangeType.list()
        assert method in TDChangeMethod.list()
        assert isinstance(data, (ThingPropertyInit, ThingActionInit, ThingEventInit))

        self.td_change_type = td_change_type
        self.method = method
        self.name = name
        self.data = data
        self.description = description