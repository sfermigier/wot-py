#!/usr/bin/env python
# -*- coding: utf-8 -*-

# noinspection PyPackageRequirements
import pytest
# noinspection PyCompatibility
from concurrent.futures import Future, ThreadPoolExecutor
# noinspection PyPackageRequirements
from faker import Faker

from tests.td_examples import TD_EXAMPLE
from tests.wot.utils import assert_exposed_thing_equal
from wotpy.wot.enums import TDChangeMethod, TDChangeType
from wotpy.wot.exposed import ExposedThing
from wotpy.wot.servient import Servient


def test_from_description():
    """ExposedThings can be created from Thing Description documents."""

    servient = Servient()
    exp_thing = ExposedThing.from_description(servient=servient, doc=TD_EXAMPLE)
    assert_exposed_thing_equal(exp_thing, TD_EXAMPLE)


def test_read_property(exposed_thing, thing_property_init):
    """Properties may be retrieved on ExposedThings."""

    exposed_thing.add_property(property_init=thing_property_init)
    future_get = exposed_thing.read_property(thing_property_init.name)

    assert future_get.result() == thing_property_init.value


def test_write_property(exposed_thing, thing_property_init):
    """Properties may be updated on ExposedThings."""

    fake = Faker()
    updated_val = fake.pystr()

    thing_property_init.writable = True
    exposed_thing.add_property(property_init=thing_property_init)
    future_set = exposed_thing.write_property(thing_property_init.name, updated_val)

    assert future_set.done()

    future_get = exposed_thing.read_property(thing_property_init.name)

    assert future_get.result() == updated_val


def test_write_non_writable_property(exposed_thing, thing_property_init):
    """Attempts to write a non-writable property should return an error."""

    fake = Faker()

    thing_property_init.writable = False
    exposed_thing.add_property(property_init=thing_property_init)

    future_write = exposed_thing.write_property(thing_property_init.name, fake.pystr())

    with pytest.raises(Exception):
        future_write.result()


def test_invoke_action(exposed_thing, thing_action_init):
    """Synchronous actions can be invoked on ExposedThings."""

    fake = Faker()
    action_arg = fake.pystr()

    executor = ThreadPoolExecutor(max_workers=1)

    def upper(val):
        return str(val).upper()

    def upper_async(val):
        return executor.submit(upper, val)

    exposed_thing.add_action(action_init=thing_action_init)
    exposed_thing.set_action_handler(action_handler=upper_async, action_name=thing_action_init.name)

    future_result = exposed_thing.invoke_action(thing_action_init.name, val=action_arg)

    assert future_result.result() == action_arg.upper()


def test_invoke_action_undefined_handler(exposed_thing, thing_action_init):
    """Actions with undefined handlers return an error."""

    exposed_thing.add_action(action_init=thing_action_init)

    future_result = exposed_thing.invoke_action(thing_action_init.name)

    with pytest.raises(Exception):
        future_result.result()

    def dummy_func():
        future = Future()
        future.set_result(True)
        return future

    exposed_thing.set_action_handler(action_handler=dummy_func, action_name=thing_action_init.name)

    future_result = exposed_thing.invoke_action(thing_action_init.name)

    assert future_result.result()


def test_on_property_change(exposed_thing, thing_property_init):
    """Property changes can be observed."""

    fake = Faker()

    prop_name = thing_property_init.name
    thing_property_init.observable = True
    exposed_thing.add_property(property_init=thing_property_init)

    observable_prop = exposed_thing.on_property_change(prop_name)

    property_values = fake.pylist(5, True, *(str,))

    emitted_values = []

    def on_next_property_event(ev):
        emitted_values.append(ev.data.value)

    subscription = observable_prop.subscribe(on_next_property_event)

    for val in property_values:
        future_write = exposed_thing.write_property(prop_name, val)
        assert future_write.done()

    assert emitted_values == property_values

    subscription.dispose()


def test_on_property_change_non_observable(exposed_thing, thing_property_init):
    """Observe requests to non-observable properties are rejected."""

    fake = Faker()

    thing_property_init.observable = False
    exposed_thing.add_property(property_init=thing_property_init)

    observable_prop = exposed_thing.on_property_change(thing_property_init.name)

    future_next = Future()
    future_error = Future()

    def on_next(item):
        future_next.set_result(item)

    def on_error(err):
        future_error.set_exception(err)

    subscription = observable_prop.subscribe(on_next=on_next, on_error=on_error)

    future_write = exposed_thing.write_property(thing_property_init.name, fake.pystr())
    assert future_write.done()

    with pytest.raises(Exception):
        future_error.result()

    assert not future_next.done()

    subscription.dispose()


def test_on_event(exposed_thing, thing_event_init):
    """Events defined in the Thing Description can be observed."""

    fake = Faker()

    event_name = thing_event_init.name
    exposed_thing.add_event(event_init=thing_event_init)

    observable_event = exposed_thing.on_event(event_name)

    event_payloads = fake.pylist(5, True, *(str,))

    emitted_payloads = []

    def on_next_event(ev):
        emitted_payloads.append(ev.data)

    subscription = observable_event.subscribe(on_next_event)

    for val in event_payloads:
        exposed_thing.emit_event(event_name, val)

    assert emitted_payloads == event_payloads

    subscription.dispose()


def test_on_td_change(exposed_thing, thing_property_init, thing_event_init, thing_action_init):
    """Thing Description changes can be observed."""

    prop_name = thing_property_init.name
    event_name = thing_event_init.name
    action_name = thing_action_init.name

    observable_td = exposed_thing.on_td_change()

    complete_futures = {
        (TDChangeType.PROPERTY, TDChangeMethod.ADD): Future(),
        (TDChangeType.PROPERTY, TDChangeMethod.REMOVE): Future(),
        (TDChangeType.EVENT, TDChangeMethod.ADD): Future(),
        (TDChangeType.EVENT, TDChangeMethod.REMOVE): Future(),
        (TDChangeType.ACTION, TDChangeMethod.ADD): Future(),
        (TDChangeType.ACTION, TDChangeMethod.REMOVE): Future()
    }

    def on_next_td_event(ev):
        change_type = ev.data.td_change_type
        change_method = ev.data.method
        interaction_name = ev.data.name
        future_key = (change_type, change_method)
        complete_futures[future_key].set_result(interaction_name)

    subscription = observable_td.subscribe(on_next_td_event)

    exposed_thing.add_event(event_init=thing_event_init)

    assert complete_futures[(TDChangeType.EVENT, TDChangeMethod.ADD)].result() == event_name
    assert not complete_futures[(TDChangeType.EVENT, TDChangeMethod.REMOVE)].done()

    exposed_thing.remove_event(name=event_name)
    exposed_thing.add_property(property_init=thing_property_init)

    assert complete_futures[(TDChangeType.EVENT, TDChangeMethod.REMOVE)].result() == event_name
    assert complete_futures[(TDChangeType.PROPERTY, TDChangeMethod.ADD)].result() == prop_name
    assert not complete_futures[(TDChangeType.PROPERTY, TDChangeMethod.REMOVE)].done()

    exposed_thing.remove_property(name=prop_name)
    exposed_thing.add_action(action_init=thing_action_init)
    exposed_thing.remove_action(name=action_name)

    assert complete_futures[(TDChangeType.PROPERTY, TDChangeMethod.REMOVE)].result() == prop_name
    assert complete_futures[(TDChangeType.ACTION, TDChangeMethod.ADD)].result() == action_name
    assert complete_futures[(TDChangeType.ACTION, TDChangeMethod.REMOVE)].result() == action_name

    subscription.dispose()
