from functools import cached_property, wraps
from inspect import Parameter, Signature, signature
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from pydantic import Required
from pydantic.config import Extra
from pydantic.main import BaseModel, create_model
from pydantic.typing import get_all_type_hints
from pydantic.utils import to_camel
from typing_extensions import ParamSpec

__all__: Sequence[str] = ("validate", "ValidatedFunction")

PS = ParamSpec("PS")
RT = TypeVar("RT")

ConfigType = Union[Type[Any], Dict[str, Any]]


@overload
def validate(
    func: None = None, *, config: Optional[ConfigType] = None
) -> Callable[[Callable[PS, RT]], Callable[PS, RT]]:
    ...


@overload
def validate(func: Callable[PS, RT]) -> Callable[PS, RT]:
    ...


def validate(
    func: Optional[Callable[PS, RT]] = None, *, config: Optional[ConfigType] = None
) -> Union[Callable[PS, RT], Callable[[Callable[PS, RT]], Callable[PS, RT]]]:
    def decorate(func: Callable[PS, RT], /) -> Callable[PS, RT]:
        validated_func: ValidatedFunction[PS, RT] = ValidatedFunction(
            func, config=config
        )

        @wraps(func)
        def wrapper(*args: PS.args, **kwargs: PS.kwargs) -> RT:
            return validated_func.call(*args, **kwargs)

        setattr(wrapper, "validator", validated_func)

        return wrapper

    if func:
        return decorate(func)
    else:
        return decorate


class ValidatedFunction(Generic[PS, RT]):
    function: Callable[PS, RT]
    model: Type[BaseModel]

    def __init__(
        self, function: Callable[PS, RT], /, *, config: Optional[ConfigType] = None
    ):
        self.function = function

        parameters: Mapping[str, Parameter] = self.signature.parameters
        type_hints: Dict[str, Any] = get_all_type_hints(function)
        fields: Dict[str, Tuple[Any, Any]] = {}

        parameter_name: str
        parameter: Parameter
        for parameter_name, parameter in parameters.items():
            annotation: Any = (
                Any
                if parameter.annotation is Parameter.empty
                else type_hints[parameter_name]
            )

            default: Any = (
                Required if parameter.default is Parameter.empty else parameter.default
            )

            if parameter.kind is Parameter.VAR_POSITIONAL:
                fields[parameter_name] = (Tuple[annotation, ...], None)
            elif parameter.kind is Parameter.VAR_KEYWORD:
                fields[parameter_name] = (Dict[str, annotation], None)
            else:
                fields[parameter_name] = (annotation, default)

        self.model = self._create_model(fields, config=config)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(function={self.function!r})>"

    def _create_model(
        self, fields: Dict[str, Any], *, config: Optional[ConfigType] = None
    ) -> Type[BaseModel]:
        CustomConfig: Type[Any]

        if isinstance(config, dict):
            CustomConfig = type("CustomConfig", (), config)
        elif isinstance(config, type):
            CustomConfig = config
        else:
            CustomConfig = type("CustomConfig", (), {})

        Config: Type[Any] = type(
            "Config",
            (CustomConfig,),
            {"extra": getattr(CustomConfig, "extra", Extra.forbid)},
        )

        ValidatedFunctionBaseModel: Type[BaseModel] = type(
            "ValidatedFunctionBaseModel", (BaseModel,), {"Config": Config}
        )

        return create_model(
            to_camel(self.function.__name__),
            __base__=ValidatedFunctionBaseModel,
            **fields,
        )

    @cached_property
    def signature(self) -> Signature:
        return signature(self.function)

    def bind_arguments(
        self, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.signature.bind(*args, **kwargs).arguments

    def prepare_arguments(
        self, arguments: Dict[str, Any], /
    ) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        args: List[Any] = []
        kwargs: Dict[str, Any] = {}

        parameter: Parameter
        for parameter in self.signature.parameters.values():
            argument: Any = arguments[parameter.name]

            if parameter.kind in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
            ):
                args.append(argument)
            elif parameter.kind is Parameter.KEYWORD_ONLY:
                kwargs[parameter.name] = argument
            elif parameter.kind is Parameter.VAR_POSITIONAL:
                args.extend(argument)
            elif parameter.kind is Parameter.VAR_KEYWORD:
                kwargs.update(argument)

        return (tuple(args), kwargs)

    def validate_arguments(
        self, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
        bound_arguments: Dict[str, Any] = self.bind_arguments(args, kwargs)
        model: BaseModel = self.model(**bound_arguments)
        arguments: Dict[str, Any] = model.dict()

        return self.prepare_arguments(arguments)

    def call(self, *args: PS.args, **kwargs: PS.kwargs) -> RT:
        validated_args: Tuple[Any, ...]
        validated_kwargs: Dict[str, Any]
        validated_args, validated_kwargs = self.validate_arguments(args, kwargs)

        return self.function(*validated_args, **validated_kwargs)
