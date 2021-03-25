#!/usr/bin/env python
# coding=utf-8
import functools
import time
import types
from datetime import timedelta

import wrapt

from sacred.config.custom_containers import fallback_dict
from sacred.config.signature import Signature
from sacred.config.utils import CMD
from sacred.randomness import create_rnd, get_seed
from sacred.utils import ConfigError

import copy


def create_captured_function(function, prefix=None, capturer=None, static_args={}):
    sig = Signature(function)
    orig_func = function
    function = copy_class_or_function(function)
    function.signature = sig
    function.uses_randomness = "_seed" in sig.arguments or "_rnd" in sig.arguments
    function.logger = None
    function.config = {}
    function.rnd = None
    function.run = None
    function.prefix = prefix
    function.capturer = capturer
    function.static_args = static_args
    return captured_function(function)


@wrapt.decorator
def captured_function(wrapped, instance, args, kwargs):
    options = fallback_dict(
        wrapped.config, _config=wrapped.config, _log=wrapped.logger, _run=wrapped.run
    )
    if wrapped.uses_randomness:  # only generate _seed and _rnd if needed
        options["_seed"] = get_seed(wrapped.rnd)
        options["_rnd"] = create_rnd(options["_seed"])

    for k in wrapped.static_args.keys():  # allow later override
        if k not in kwargs:
            kwargs[k] = wrapped.static_args[k]
            # @todo maybe a warning or expection in case of static vs config

    bound = instance is not None
    args, kwargs = wrapped.signature.construct_arguments(args, kwargs, options, bound)
    for k, v in kwargs.items():
        if isinstance(v, CMD):
            kwargs[k] = exec_config_commmand(wrapped.capturer, v)
    if wrapped.logger is not None:
        wrapped.logger.debug("Started")
        start_time = time.time()
    # =================== run actual function =================================
    with ConfigError.track(wrapped):
        result = wrapped(*args, **kwargs)
    # =========================================================================
    if wrapped.logger is not None:
        stop_time = time.time()
        elapsed_time = timedelta(seconds=round(stop_time - start_time))
        wrapped.logger.debug("Finished after %s.", elapsed_time)

    return result


def exec_config_commmand(ing, cmd):
    # @todo some docmentation of this syntax
    # @todo some tests
    if cmd.startswith("/"):
        # command not ingredient specific
        # execute it globally (removing the / char)
        return ing.current_run.get_command_function(cmd[1:])()
    if cmd.startswith("."):
        # command has a relative path to the current ing
        return ing.current_run.get_command_function(ing.path + cmd)()
    return ing.commands[cmd]()


def copy_class_or_function(obj):
    if types.FunctionType == type(obj):
        return copy_func(obj)
    if types.MethodType == type(obj):
        # copy the function
        tmp_func = copy_func(obj)
        # bind it to the previous instance
        return tmp_func.__get__(obj.__self__, obj.__self__.__class__)

    # @todo maybe not a class or a function
    def get_class_copy(cls):
        class CLS_wrap(cls):
            pass

        CLS_wrap.__name__ = cls.__name__
        return CLS_wrap

    return get_class_copy(obj)
    # return type(obj.__name__, obj.__bases__, dict(obj.__dict__))


def copy_func(f):
    """Based on http://stackoverflow.com/a/6528148/190597 (Glenn Maynard)"""
    g = types.FunctionType(
        f.__code__,
        f.__globals__,
        name=f.__name__,
        argdefs=f.__defaults__,
        closure=f.__closure__,
    )
    g = functools.update_wrapper(g, f)
    g.__kwdefaults__ = f.__kwdefaults__
    return g
