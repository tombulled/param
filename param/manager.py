import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Union, TypeVar

from .enums import ParameterType
from .errors import MissingSpecification
from .models import Arguments, BoundArguments, Parameter
from .parameters import Param, ParameterSpecification
from .resolvers import Resolvers, resolve_param
from .sentinels import Missing, MissingType

T = TypeVar("T")


def _parse(value: Any, /) -> Any:
    if value is inspect._empty:
        return Missing

    return value


def _bind_arguments(func: Callable[..., Any], arguments: Arguments) -> BoundArguments:
    signature: inspect.Signature = inspect.signature(func)

    bound_arguments: inspect.BoundArguments = arguments.call(signature.bind)

    bound_arguments.apply_defaults()

    bound_args: Dict[str, Any] = dict(zip(signature.parameters, bound_arguments.args))
    bound_kwargs: Dict[str, Any] = bound_arguments.kwargs

    return BoundArguments(args=bound_args, kwargs=bound_kwargs)


@dataclass
class ParameterManager(Generic[T]):
    resolvers: Resolvers[T]

    def get_params(self, func: Callable, /) -> Dict[str, Parameter]:
        params: Dict[str, Parameter] = {}

        parameter: inspect.Parameter
        for parameter in inspect.signature(func).parameters.values():
            spec: ParameterSpecification

            if isinstance(parameter.default, ParameterSpecification):
                spec = parameter.default
            else:
                spec = self.infer_parameter(parameter)

            param: Parameter = Parameter(
                name=parameter.name,
                annotation=_parse(parameter.annotation),
                type=ParameterType.from_kind(parameter.kind),
                spec=spec,
            )

            params[parameter.name] = param

        return params

    def infer_parameter(
        self, parameter: inspect.Parameter, /
    ) -> ParameterSpecification:
        raise MissingSpecification(f"Missing specification for parameter {parameter}")

    def resolve(self, parameter: Parameter, argument: Any) -> Any:
        return self.resolvers.resolve(parameter, argument)

    def resolve_parameters(self, parameters: Dict[str, Parameter], arguments: Dict[str, Any], /) -> Dict[str, Any]:
        return {
            parameter.name: self.resolve(parameter, argument)
            for parameter, argument in zip(parameters.values(), arguments.values())
        }

    def get_arguments(self, func: Callable, arguments: Arguments) -> BoundArguments:
        bound_arguments: BoundArguments = _bind_arguments(func, arguments)

        parameters: Dict[str, Parameter] = self.get_params(func)

        parameters_to_resolve: Dict[str, Parameter] = {}

        source: Dict[str, Any]
        for source in (bound_arguments.args, bound_arguments.kwargs):
            parameter_name: str
            argument: Any
            for parameter_name, argument in source.items():
                parameter: Parameter = parameters[parameter_name]

                if isinstance(argument, ParameterSpecification):
                    # if argument is parameter.spec:
                    #     argument = Missing

                    # source[parameter_name] = self.resolve(parameter, argument)

                    parameters_to_resolve[parameter_name] = parameter

        resolved_arguments: Dict[str, Any] = self.resolve_parameters(parameters_to_resolve, bound_arguments.arguments)

        for parameter_name, argument in resolved_arguments.items():
            source = bound_arguments.args if parameter_name in bound_arguments.args else bound_arguments.kwargs

            source[parameter_name] = argument

        return bound_arguments


@dataclass
class ParamManager(ParameterManager[Union[Any, MissingType]]):
    resolvers: Resolvers[Union[Any, MissingType]] = field(
        default_factory=lambda: Resolvers({Param: resolve_param})
    )

    def infer_parameter(
        self, parameter: inspect.Parameter, /
    ) -> ParameterSpecification:
        return Param(default=_parse(parameter.default))
