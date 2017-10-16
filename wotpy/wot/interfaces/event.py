#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractproperty


class AbstractEvent(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def data(self):
        pass