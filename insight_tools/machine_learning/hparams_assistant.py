from typing import Union as U, Optional as Opt, Callable, Any, Dict
from collections import defaultdict
from functools import partial
from itertools import chain
from argparse import Namespace
import inspect
import logging

from toposort import toposort


logger = logging.getLogger(__name__)


def generate_type_hints(setted_params: Dict[str, any]):
    type_hints = '\nAdd to your model: \n\n'
    type_hints += f'class CoolModel:\n'
    for param_name, obj in setted_params.items():
        type_hints += f'    {param_name}: {type(obj).__name__}\n'

    type_hints += '\n    def __init__(...):\n'
    type_hints += '    ...'
    return type_hints


class HParamsAssistant:

    def __init__(
            self,
            str_to_type: Opt[Dict[str, type]] = None,
            save_all_params_to_model: bool = False,
            raise_import_error: bool = True,
            raise_unknown_named_object: bool = True,
            return_partial: bool = True):

        self.str_to_type = str_to_type
        self.save_all_params_to_model = save_all_params_to_model
        self.raise_import_error = raise_import_error
        self.raise_unknown_named_object = raise_unknown_named_object
        self.return_partial = return_partial

        self.parameter_factories = defaultdict(dict)
        self.class_nicknames = {}

    def get_object(self, setted_params: Dict[str, Any],
                   param_name: str, packed_object):
        obj = None
        if self.is_unpackable(packed_object):
            packed_object = self.set_params_in_packed_object(setted_params,
                                                             packed_object)
            obj = self.unpack_object(packed_object)
        elif self.is_named_object(param_name, packed_object):
            obj = self.get_named_object(param_name, packed_object)

        if obj is None and self.save_all_params_to_model:
            obj = packed_object

        return obj

    def parametrize(self, hparams: U[dict, Namespace],
                    model: Any = None,
                    print_type_hints: bool = False) -> Dict[str, Any]:
        setted_params = {}
        if isinstance(hparams, Namespace):
            hparams = hparams.__dict__

        if self.str_to_type is None:
            if model is not None:
                # take imported modules in model file
                module = inspect.getmodule(model)
                self.str_to_type = module.__dict__
                logger.info(f'String to type map taken from imports of module '
                            f'{module.__name__}')
            else:
                # take imported modules in calling function
                module = inspect.getmodule(inspect.stack()[1][0])
                self.str_to_type = module.__dict__
                logger.info(f'String to type map taken from imports of module '
                            f'of calling function {module.__name__}')

        for param_name, packed_object in hparams.items():
            obj = self.get_object(setted_params, param_name, packed_object)

            # set model parameter
            if obj is not None:
                setted_params[param_name] = obj
                if model is not None:
                    setattr(model, param_name, obj)

        if print_type_hints:
            print(generate_type_hints(setted_params))

        return setted_params

    def unpack_object(self, object_dict: dict):
        if self.str_to_type is None:
            raise ValueError('Objects cannot be unpacked without mapping from '
                             'string to its type')
        kwargs = object_dict.copy()
        cls_name = kwargs.pop('__class__')
        if 'args' in kwargs:
            args = kwargs.pop('args')
        else:
            args = []
        if cls_name in self.class_nicknames:
            cls_name = self.class_nicknames[cls_name]

        try:
            cls = self.str_to_type[cls_name]
            return cls(*args, **kwargs)
        except TypeError as e:
            if self.return_partial:
                return partial(cls, **kwargs)
            raise e
        except AttributeError:
            if self.raise_import_error:
                raise ImportError(name=cls_name)
            logger.warning(f"Can't find class {cls_name} in str_to_class dict")
        return None

    def get_named_object(self, param_name: str, factory_name: str):
        factories = self.parameter_factories[param_name]
        if factory_name in factories:
            return factories[factory_name]()
        else:
            msg = f"Can't find named object {factory_name} " \
                  f"for parameter {param_name}."
            if self.raise_unknown_named_object:
                raise ValueError(msg)
            else:
                logger.warning(msg)

        return None

    @staticmethod
    def is_unpackable(packed_object):
        return isinstance(packed_object, dict) and '__class__' in packed_object

    def is_named_object(self, param_name, packed_object):
        return param_name in self.parameter_factories \
               and isinstance(packed_object, str)

    @staticmethod
    def value_is_another_hparam(value):
        return isinstance(value, str) and value.startswith('$')

    def add_named_object(self, param_name: str, object_name: str,
                         obj: Any = None,
                         object_factory: U[Callable[[], Any]] = None):
        # xor
        only_one_setted = (obj is not None) != (object_factory is not None)
        assert only_one_setted, \
            'Either obj or object_factory must be not None'

        if object_factory is None:
            def object_factory():
                return obj
        self.parameter_factories[param_name][object_name] = object_factory

    def add_class_nickname(self, class_name: str, nickname: str):
        self.class_nicknames[nickname] = class_name

    @staticmethod
    def set_params_in_packed_object(setted_params: Dict[str, Any],
                                    packed_object: dict):
        res = packed_object.copy()
        for attr, value in res.items():
            if attr == 'args':
                args = value
                for i, v in enumerate(args):
                    if HParamsAssistant.value_is_another_hparam(v):
                        args[i] = setted_params[v[1:]]
            elif HParamsAssistant.value_is_another_hparam(value):
                res[attr] = setted_params[value[1:]]
        return res

    @staticmethod
    def order_hparams_topologically(hparams: dict):
        dependency_graph = defaultdict(set)
        for parameter_name, packed_object in hparams.items():
            if HParamsAssistant.is_unpackable(packed_object):
                for attr, value in packed_object.items():
                    if HParamsAssistant.value_is_another_hparam(value):
                        dependency_graph[parameter_name].add(value[1:])

        return chain.from_iterable(toposort(dependency_graph))
