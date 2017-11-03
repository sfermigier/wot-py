#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from jsonschema import validate, ValidationError

from wotpy.protocols.ws.enums import WebsocketErrors
from wotpy.protocols.ws.schemas import \
    SCHEMA_REQUEST, \
    SCHEMA_RESPONSE, \
    SCHEMA_EMITTED_ITEM, \
    SCHEMA_ERROR, \
    JSON_RPC_VERSION


class WebsocketMessageException(Exception):
    """Exception raised when a WS message appears to be invalid."""

    pass


class WebsocketMessageRequest(object):
    """Represents a message received on a websocket that
    contains a JSON-RPC WoT action request."""

    @classmethod
    def from_raw(cls, raw_msg):
        """Builds a new WebsocketMessageRequest instance from a raw socket message.
        Raises WebsocketMessageException if the message is invalid."""

        try:
            request_msg = json.loads(raw_msg)
            validate(request_msg, SCHEMA_REQUEST)

            return WebsocketMessageRequest(
                method=request_msg["method"],
                params=request_msg["params"],
                req_id=request_msg.get("id", None))
        except Exception as ex:
            raise WebsocketMessageException(str(ex))

    def __init__(self, method, params, req_id=None):
        self.method = method
        self.params = params
        self.req_id = req_id

        try:
            validate(self.to_dict(), SCHEMA_REQUEST)
        except ValidationError as ex:
            raise WebsocketMessageError(str(ex))

    def to_dict(self):
        """Returns this message as a dict."""

        msg = {
            "jsonrpc": JSON_RPC_VERSION,
            "method": self.method,
            "params": self.params,
            "id": self.req_id
        }

        return msg

    def to_json(self):
        """Returns this message as a JSON string."""

        return json.dumps(self.to_dict())


class WebsocketMessageResponse(object):
    """Represents a WoT Websockets JSON-RPC response message."""

    @classmethod
    def from_raw(cls, raw_msg):
        """Builds a new WebsocketMessageResponse instance from a raw socket message.
        Raises WebsocketMessageException if the message is invalid."""

        try:
            response_msg = json.loads(raw_msg)
            validate(response_msg, SCHEMA_RESPONSE)

            return WebsocketMessageResponse(
                result=response_msg["result"],
                res_id=response_msg.get("id", None))
        except Exception as ex:
            raise WebsocketMessageException(str(ex))

    def __init__(self, result, res_id=None):
        self.result = result
        self.res_id = res_id

        try:
            validate(self.to_dict(), SCHEMA_RESPONSE)
        except ValidationError as ex:
            raise WebsocketMessageError(str(ex))

    def to_dict(self):
        """Returns this message as a dict."""

        msg = {
            "jsonrpc": JSON_RPC_VERSION,
            "result": self.result,
            "id": self.res_id
        }

        return msg

    def to_json(self):
        """Returns this message as a JSON string."""

        return json.dumps(self.to_dict())


class WebsocketMessageError(object):
    """Represents a WoT Websockets JSON-RPC error message."""

    @classmethod
    def from_raw(cls, raw_msg):
        """Builds a new WebsocketMessageError instance from a raw socket message.
        Raises WebsocketMessageException if the message is invalid."""

        try:
            error_msg = json.loads(raw_msg)
            validate(error_msg, SCHEMA_ERROR)

            return WebsocketMessageError(
                message=error_msg["error"]["message"],
                code=error_msg["error"]["code"],
                res_id=error_msg.get("id", None))
        except Exception as ex:
            raise WebsocketMessageException(str(ex))

    def __init__(self, message, code=WebsocketErrors.INTERNAL_ERROR, res_id=None):
        self.message = message
        self.res_id = res_id
        self.code = code

        try:
            validate(self.to_dict(), SCHEMA_ERROR)
        except ValidationError as ex:
            raise WebsocketMessageError(str(ex))

    def to_dict(self):
        """Returns this message as a dict."""

        msg = {
            "jsonrpc": JSON_RPC_VERSION,
            "error": {
                "code": self.code,
                "message": self.message
            },
            "id": self.res_id
        }

        return msg

    def to_json(self):
        """Returns this message as a JSON string."""

        return json.dumps(self.to_dict())


class WebsocketMessageEmittedItem(object):
    """Represents a Websockets message for an items emitted by an Observable."""

    @classmethod
    def from_raw(cls, raw_msg):
        """Builds a new WebsocketMessageEmittedItem instance from a raw socket message.
        Raises WebsocketMessageException if the message is invalid."""

        try:
            msg = json.loads(raw_msg)
            validate(msg, SCHEMA_EMITTED_ITEM)

            return WebsocketMessageEmittedItem(
                subscription_id=msg["subscription"],
                name=msg["name"],
                data=msg["data"])
        except Exception as ex:
            raise WebsocketMessageException(str(ex))

    def __init__(self, subscription_id, name, data):
        self.subscription_id = subscription_id
        self.name = name
        self.data = data if isinstance(data, dict) else data.__dict__

        try:
            validate(self.to_dict(), SCHEMA_EMITTED_ITEM)
        except ValidationError as ex:
            raise WebsocketMessageError(str(ex))

    def to_dict(self):
        """Returns this message as a dict."""

        msg = {
            "subscription": self.subscription_id,
            "name": self.name,
            "data": self.data
        }

        return msg

    def to_json(self):
        """Returns this message as a JSON string."""

        return json.dumps(self.to_dict())