#!/usr/bin/env python
# -*- coding: utf-8 -*-
import uuid

import pytest
import six
import tornado.concurrent
import tornado.gen
import tornado.ioloop
import tornado.websocket
from faker import Faker
from rx.concurrency import IOLoopScheduler

from wotpy.protocols.coap.client import CoAPClient
from wotpy.td.description import ThingDescription


@pytest.mark.flaky(reruns=5)
def test_read_property(coap_servient):
    """The CoAP client can read properties."""

    exposed_thing = next(coap_servient.exposed_things)
    td = ThingDescription.from_thing(exposed_thing.thing)

    @tornado.gen.coroutine
    def test_coroutine():
        coap_client = CoAPClient()
        prop_name = next(six.iterkeys(td.properties))
        prop_value = Faker().sentence()

        coap_prop_value = yield coap_client.read_property(td, prop_name)
        assert coap_prop_value != prop_value

        yield exposed_thing.properties[prop_name].write(prop_value)

        coap_prop_value = yield coap_client.read_property(td, prop_name)
        assert coap_prop_value == prop_value

    tornado.ioloop.IOLoop.current().run_sync(test_coroutine)


@pytest.mark.flaky(reruns=5)
def test_write_property(coap_servient):
    """The CoAP client can write properties."""

    exposed_thing = next(coap_servient.exposed_things)
    td = ThingDescription.from_thing(exposed_thing.thing)

    @tornado.gen.coroutine
    def test_coroutine():
        coap_client = CoAPClient()
        prop_name = next(six.iterkeys(td.properties))
        prop_value = Faker().sentence()

        prev_value = yield exposed_thing.properties[prop_name].read()
        assert prev_value != prop_value

        yield coap_client.write_property(td, prop_name, prop_value)

        curr_value = yield exposed_thing.properties[prop_name].read()
        assert curr_value == prop_value

    tornado.ioloop.IOLoop.current().run_sync(test_coroutine)


@pytest.mark.flaky(reruns=5)
def test_invoke_action(coap_servient):
    """The CoAP client can invoke actions."""

    exposed_thing = next(coap_servient.exposed_things)
    td = ThingDescription.from_thing(exposed_thing.thing)

    @tornado.gen.coroutine
    def test_coroutine():
        coap_client = CoAPClient()
        action_name = next(six.iterkeys(td.actions))
        input_value = Faker().pyint()

        @tornado.gen.coroutine
        def double(parameters):
            yield tornado.gen.sleep(0.1)
            raise tornado.gen.Return(parameters.get("input") * 2)

        exposed_thing.set_action_handler(action_name, double)

        result = yield coap_client.invoke_action(td, action_name, input_value)

        assert result == input_value * 2

    tornado.ioloop.IOLoop.current().run_sync(test_coroutine)


@pytest.mark.flaky(reruns=5)
def test_on_property_change(coap_servient):
    """The CoAP client can subscribe to property updates."""

    exposed_thing = next(coap_servient.exposed_things)
    td = ThingDescription.from_thing(exposed_thing.thing)

    @tornado.gen.coroutine
    def test_coroutine():
        coap_client = CoAPClient()

        property_name = next(six.iterkeys(td.properties))

        observable = coap_client.on_property_change(td, property_name)

        values = [Faker().sentence() for _ in range(10)]
        values_observed = {value: tornado.concurrent.Future() for value in values}

        @tornado.gen.coroutine
        def write_next_value():
            next_value = next(val for val, fut in six.iteritems(values_observed) if not fut.done())
            yield exposed_thing.properties[property_name].write(next_value)

        def on_next(ev):
            prop_value = ev.data.value
            if prop_value in values_observed and not values_observed[prop_value].done():
                values_observed[prop_value].set_result(True)

        subscription = observable.subscribe_on(IOLoopScheduler()).subscribe(on_next)

        periodic_emit = tornado.ioloop.PeriodicCallback(write_next_value, 10)
        periodic_emit.start()

        yield list(values_observed.values())

        periodic_emit.stop()
        subscription.dispose()

    tornado.ioloop.IOLoop.current().run_sync(test_coroutine)


@pytest.mark.flaky(reruns=5)
def test_on_event(coap_servient):
    """The CoAP client can subscribe to event emissions."""

    exposed_thing = next(coap_servient.exposed_things)
    td = ThingDescription.from_thing(exposed_thing.thing)

    @tornado.gen.coroutine
    def test_coroutine():
        coap_client = CoAPClient()

        event_name = next(six.iterkeys(td.events))

        observable = coap_client.on_event(td, event_name)

        payloads = [uuid.uuid4().hex for _ in range(10)]
        future_payloads = {key: tornado.concurrent.Future() for key in payloads}

        @tornado.gen.coroutine
        def emit_next_event():
            next_value = next(val for val, fut in six.iteritems(future_payloads) if not fut.done())
            exposed_thing.events[event_name].emit(next_value)

        def on_next(ev):
            if ev.data in future_payloads and not future_payloads[ev.data].done():
                future_payloads[ev.data].set_result(True)

        subscription = observable.subscribe_on(IOLoopScheduler()).subscribe(on_next)

        periodic_emit = tornado.ioloop.PeriodicCallback(emit_next_event, 10)
        periodic_emit.start()

        yield list(future_payloads.values())

        periodic_emit.stop()
        subscription.dispose()

    tornado.ioloop.IOLoop.current().run_sync(test_coroutine)