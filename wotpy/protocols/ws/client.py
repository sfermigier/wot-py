#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classes that contain the client logic for the Websocket protocol.
"""

import uuid

import tornado.gen
import tornado.websocket
from rx import Observable
from six.moves import urllib
from tornado.concurrent import Future

from wotpy.protocols.client import BaseProtocolClient, ProtocolClientException
from wotpy.protocols.enums import ProtocolSchemes, Protocols
from wotpy.protocols.ws.enums import WebsocketMethods
from wotpy.protocols.ws.messages import \
    WebsocketMessageRequest, \
    WebsocketMessageResponse, \
    WebsocketMessageEmittedItem, \
    WebsocketMessageError, \
    WebsocketMessageException
from wotpy.wot.dictionaries import \
    PropertyChangeEventInit, \
    ThingDescriptionChangeEventInit, \
    ThingActionInit, \
    ThingPropertyInit, \
    ThingEventInit
from wotpy.wot.enums import TDChangeType
from wotpy.wot.events import \
    PropertyChangeEmittedEvent, \
    EmittedEvent, \
    ThingDescriptionChangeEmittedEvent


class WebsocketClient(BaseProtocolClient):
    """Implementation of the protocol client interface for the Websocket protocol."""

    @classmethod
    def _pick_form(cls, td, forms):
        """Picks the Form that will be used to connect to the remote Thing."""

        def is_form_for_scheme(form, scheme):
            resolved_url = td.resolve_form_uri(form)

            if not resolved_url:
                return False

            return urllib.parse.urlparse(resolved_url).scheme == scheme

        def is_ws_form(form):
            return is_form_for_scheme(form, ProtocolSchemes.WS)

        def is_wss_form(form):
            return is_form_for_scheme(form, ProtocolSchemes.WSS)

        forms_wss = [item for item in forms if is_wss_form(item)]

        if len(forms_wss):
            return forms_wss[0]

        forms_ws = [item for item in forms if is_ws_form(item)]

        if len(forms_ws):
            return forms_ws[0]

        return None

    @classmethod
    def _parse_response(cls, raw_msg, msg_id):
        """Returns a parsed WS Response message instance if
        the raw message format is valid and has the given ID.
        Raises Exception if the WS message is an error."""

        try:
            msg = WebsocketMessageResponse.from_raw(raw_msg)

            if msg.id == msg_id:
                return msg
        except WebsocketMessageException:
            pass

        try:
            err = WebsocketMessageError.from_raw(raw_msg)

            if err.id == msg_id:
                raise Exception(err.message)
        except WebsocketMessageException:
            pass

        return None

    @classmethod
    def _parse_emitted_item(cls, raw_msg, sub_id):
        """Returns a parsed WS Emitted Item message instance if
        the raw message format is valid and has the given ID.
        Raises Exception if the WS message is an error."""

        try:
            msg = WebsocketMessageEmittedItem.from_raw(raw_msg)

            if msg.subscription_id == sub_id:
                return msg
        except WebsocketMessageException:
            pass

        try:
            err = WebsocketMessageError.from_raw(raw_msg)
            err_sub_id = err.data and err.data.get("subscription")

            if err_sub_id == sub_id:
                raise Exception(err.message)
        except WebsocketMessageException:
            pass

        return None

    @property
    def protocol(self):
        """Protocol of this client instance.
        A member of the Protocols enum."""

        return Protocols.WEBSOCKETS

    def _build_subscribe(self, ws_url, msg_req, on_next):
        """Builds the subscribe function that is passed
        as an argument on the creation of an Observable."""

        def subscribe(observer):
            """Connect to the WS server and start passing the received events to the Observer."""

            future_sub_id = Future()
            future_ws_conn = Future()

            def on_error(ex):
                observer.on_error(ex)

            def on_next_event(raw_msg):
                sub_id = future_sub_id.result()

                try:
                    msg_item = self._parse_emitted_item(raw_msg, sub_id)
                except Exception as ex:
                    return on_error(ex)

                if msg_item is None:
                    return

                try:
                    on_next(observer, msg_item)
                except Exception as ex:
                    return on_error(ex)

            def parse_subscription_id(raw_msg):
                try:
                    msg_res = self._parse_response(raw_msg, msg_req.id)
                except Exception as ex:
                    return on_error(ex)

                if msg_res is None:
                    return

                sub_id = msg_res.result
                future_sub_id.set_result(sub_id)

            def on_msg(raw_msg):
                if raw_msg is None:
                    return on_error(Exception("WS connection closed"))

                if future_sub_id.done():
                    on_next_event(raw_msg)
                else:
                    parse_subscription_id(raw_msg)

            def on_conn(ft):
                try:
                    ws_conn = ft.result()
                except Exception as ex:
                    return on_error(ex)

                future_ws_conn.set_result(ws_conn)
                ws_conn.write_message(msg_req.to_json())

            tornado.websocket.websocket_connect(ws_url, callback=on_conn, on_message_callback=on_msg)

            def unsubscribe():
                if future_ws_conn.done():
                    ws_conn = future_ws_conn.result()
                    ws_conn.close()

            return unsubscribe

        return subscribe

    @tornado.gen.coroutine
    def _wait_for_response(self, ws_conn, msg_id):
        """Waits for the WebSocket response message that matches the given ID."""

        while True:
            raw_res = yield ws_conn.read_message()

            if raw_res is None:
                raise Exception("WS connection closed")

            msg_res = self._parse_response(raw_res, msg_id)

            if msg_res is not None:
                raise tornado.gen.Return(msg_res.result)

    @tornado.gen.coroutine
    def _send_websocket_message(self, ws_url, msg_req):
        """Sends a WebSocket request message, waits for the response and returns the result."""

        ws_conn = yield tornado.websocket.websocket_connect(ws_url)
        ws_conn.write_message(msg_req.to_json())

        result = yield self._wait_for_response(ws_conn, msg_req.id)

        yield ws_conn.close()

        raise tornado.gen.Return(result)

    @tornado.gen.coroutine
    def invoke_action(self, td, name, *args, **kwargs):
        """Invokes an Action on a remote Thing.
        Returns a Future."""

        form = self._pick_form(td, td.get_action_forms(name))

        if not form:
            raise ProtocolClientException()

        ws_url = td.resolve_form_uri(form)

        msg_req = WebsocketMessageRequest(
            method=WebsocketMethods.INVOKE_ACTION,
            params={"name": name, "parameters": kwargs},
            msg_id=uuid.uuid4().hex)

        result = yield self._send_websocket_message(ws_url, msg_req)

        raise tornado.gen.Return(result)

    @tornado.gen.coroutine
    def write_property(self, td, name, value):
        """Updates the value of a Property on a remote Thing.
        Returns a Future."""

        form = self._pick_form(td, td.get_property_forms(name))

        if not form:
            raise ProtocolClientException()

        ws_url = td.resolve_form_uri(form)

        msg_req = WebsocketMessageRequest(
            method=WebsocketMethods.WRITE_PROPERTY,
            params={"name": name, "value": value},
            msg_id=uuid.uuid4().hex)

        result = yield self._send_websocket_message(ws_url, msg_req)

        raise tornado.gen.Return(result)

    @tornado.gen.coroutine
    def read_property(self, td, name):
        """Reads the value of a Property on a remote Thing.
        Returns a Future."""

        form = self._pick_form(td, td.get_property_forms(name))

        if not form:
            raise ProtocolClientException()

        ws_url = td.resolve_form_uri(form)

        msg_req = WebsocketMessageRequest(
            method=WebsocketMethods.READ_PROPERTY,
            params={"name": name},
            msg_id=uuid.uuid4().hex)

        result = yield self._send_websocket_message(ws_url, msg_req)

        raise tornado.gen.Return(result)

    def on_event(self, td, name):
        """Subscribes to an event on a remote Thing.
        Returns an Observable."""

        form = self._pick_form(td, td.get_event_forms(name))

        if not form:
            # noinspection PyUnresolvedReferences
            return Observable.throw(ProtocolClientException())

        ws_url = td.resolve_form_uri(form)

        msg_req = WebsocketMessageRequest(
            method=WebsocketMethods.ON_EVENT,
            params={"name": name},
            msg_id=uuid.uuid4().hex)

        def on_next(observer, msg_item):
            observer.on_next(EmittedEvent(init=msg_item.data, name=name))

        subscribe = self._build_subscribe(ws_url, msg_req, on_next)

        # noinspection PyUnresolvedReferences
        return Observable.create(subscribe)

    def on_property_change(self, td, name):
        """Subscribes to property changes on a remote Thing.
        Returns an Observable."""

        form = self._pick_form(td, td.get_property_forms(name))

        if not form:
            # noinspection PyUnresolvedReferences
            return Observable.throw(ProtocolClientException())

        ws_url = td.resolve_form_uri(form)

        msg_req = WebsocketMessageRequest(
            method=WebsocketMethods.ON_PROPERTY_CHANGE,
            params={"name": name},
            msg_id=uuid.uuid4().hex)

        def on_next(observer, msg_item):
            init_name = msg_item.data["name"]
            init_value = msg_item.data["value"]
            init = PropertyChangeEventInit(name=init_name, value=init_value)
            observer.on_next(PropertyChangeEmittedEvent(init=init))

        subscribe = self._build_subscribe(ws_url, msg_req, on_next)

        # noinspection PyUnresolvedReferences
        return Observable.create(subscribe)

    def on_td_change(self, td):
        """Subscribes to Thing Description changes on a remote Thing.
        Returns an Observable."""

        base_url = td.base

        if not base_url:
            # noinspection PyUnresolvedReferences
            return Observable.throw(ProtocolClientException("Undefined base URI"))

        parsed_base_url = urllib.parse.urlparse(base_url)
        # noinspection PyProtectedMember
        ws_url = parsed_base_url._replace(scheme=ProtocolSchemes.WS).geturl()

        msg_req = WebsocketMessageRequest(
            method=WebsocketMethods.ON_TD_CHANGE,
            params={},
            msg_id=uuid.uuid4().hex)

        type_init_map = {
            TDChangeType.PROPERTY: ThingPropertyInit,
            TDChangeType.ACTION: ThingActionInit,
            TDChangeType.EVENT: ThingEventInit
        }

        def on_next(observer, msg_item):
            item_data = msg_item.data or {}
            change_type = item_data.get("td_change_type")

            init_kwargs = {
                "td_change_type": change_type,
                "method": item_data.get("method"),
                "name": item_data.get("name"),
                "description": item_data.get("description")
            }

            if change_type in type_init_map:
                interaction_init_klass = type_init_map[change_type]
                init_data = interaction_init_klass(**item_data.get("data", {}))
                init_kwargs.update({"data": init_data})

            init = ThingDescriptionChangeEventInit(**init_kwargs)

            observer.on_next(ThingDescriptionChangeEmittedEvent(init=init))

        subscribe = self._build_subscribe(ws_url, msg_req, on_next)

        # noinspection PyUnresolvedReferences
        return Observable.create(subscribe)