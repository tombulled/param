from typing import Any, Callable, Dict

from pydantic.fields import Undefined
from pytest import fixture

from param import Param, manager, parameters, params
from param.api import MANAGER, get_arguments, get_parameters
from param.enums import ParameterType
from param.models import Arguments, BoundArguments, Parameter, Resolvable
from param.wrappers import Param


class Class:
    @params
    def get(
        self, url: str, params: dict = Param(default_factory=dict)
    ) -> Dict[str, Any]:
        return dict(self=self, url=url, params=params)

    @classmethod
    @params
    def post(
        cls, url: str, params: dict = Param(default_factory=dict)
    ) -> Dict[str, Any]:
        return dict(cls=cls, url=url, params=params)

    @staticmethod
    @params
    def put(url: str, params: dict = Param(default_factory=dict)) -> Dict[str, Any]:
        return dict(url=url, params=params)


@fixture
def func() -> Callable:
    @params
    def func(message: str = Param(default="Hello, World!")) -> str:
        return message

    return func


def test_params_func(func: Callable):
    assert func() == "Hello, World!"
    assert func("Hello, Aliens!") == "Hello, Aliens!"


def test_params_instance_method():
    obj: Class = Class()

    assert obj.get("/foo") == dict(self=obj, url="/foo", params={})
    assert obj.get("/foo", {"query": "fish"}) == dict(
        self=obj, url="/foo", params={"query": "fish"}
    )


def test_params_class_method():
    obj: Class = Class()

    assert obj.post("/foo") == dict(cls=Class, url="/foo", params={})
    assert Class.post("/foo") == dict(cls=Class, url="/foo", params={})
    assert obj.post("/foo", {"query": "fish"}) == dict(
        cls=Class, url="/foo", params={"query": "fish"}
    )
    assert Class.post("/foo", {"query": "fish"}) == dict(
        cls=Class, url="/foo", params={"query": "fish"}
    )


def test_params_static_method():
    obj: Class = Class()

    assert obj.put("/foo") == dict(url="/foo", params={})
    assert Class.put("/foo") == dict(url="/foo", params={})
    assert obj.put("/foo", {"query": "fish"}) == dict(
        url="/foo", params={"query": "fish"}
    )
    assert Class.put("/foo", {"query": "fish"}) == dict(
        url="/foo", params={"query": "fish"}
    )


def test_get_params() -> None:
    def func(a: int, b: str = "b", **c: bool) -> None:
        ...

    assert get_parameters(func) == {
        "a": Parameter(
            name="a",
            default=Undefined,
            annotation=int,
            type=ParameterType.POSITIONAL_OR_KEYWORD,
        ),
        "b": Parameter(
            name="b",
            default="b",
            annotation=str,
            type=ParameterType.POSITIONAL_OR_KEYWORD,
        ),
        "c": Parameter(
            name="c",
            default=Undefined,
            annotation=bool,
            type=ParameterType.VAR_KEYWORD,
        ),
    }


def test_get_resolvables() -> None:
    def func(a: int, b: str = "b", c: bool = Param(default=True)) -> None:
        ...

    assert MANAGER.get_resolvables(func, Arguments(args=(123,))) == {
        "a": Resolvable(
            parameter=Parameter(
                name="a",
                default=Undefined,
                annotation=int,
                type=ParameterType.POSITIONAL_OR_KEYWORD,
            ),
            field=parameters.Param(alias="a"),
            argument=123,
        ),
        "b": Resolvable(
            parameter=Parameter(
                name="b",
                default="b",
                annotation=str,
                type=ParameterType.POSITIONAL_OR_KEYWORD,
            ),
            field=parameters.Param(alias="b", default="b"),
            argument="b",
        ),
        "c": Resolvable(
            parameter=Parameter(
                name="c",
                default=parameters.Param(default=True),
                annotation=bool,
                type=ParameterType.POSITIONAL_OR_KEYWORD,
            ),
            field=parameters.Param(alias="c", default=True),
            argument=Undefined,
        ),
    }


def test_get_arguments() -> None:
    def func(a: int, b: str = "b", c: bool = Param(default=True)) -> None:
        ...

    assert get_arguments(func, Arguments(args=(123,))) == BoundArguments(
        args={"a": 123, "b": "b", "c": True}, kwargs={}
    )


def test_get_bound_arguments() -> None:
    def func(a: int, b: str = "b", c: bool = Param(default=True)) -> None:
        ...

    assert manager._bind_arguments(func, Arguments(args=(123,))) == BoundArguments(
        args={"a": 123, "b": "b", "c": Param(default=True)},
        kwargs={},
    )
