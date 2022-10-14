from typing import Any, Callable, Protocol, Type, TypeVar

from pydantic.fields import Undefined
from roster import Register

from . import utils
from .errors import ResolutionError
from .models import Resolvable
from .parameters import Param

R = TypeVar("R", bound=Callable)


class Resolver(Protocol):
    def __call__(self, resolvable: Resolvable, /) -> Any:
        ...


class Resolvers(Register[Type[Param], R]):
    pass


RESOLVERS: Resolvers[Resolver] = Resolvers()


@RESOLVERS(Param)
def resolve_param(resolvable: Resolvable[Param], /) -> Any:
    if resolvable.argument is not Undefined:
        return resolvable.argument
    elif utils.has_default(resolvable.field):
        return utils.get_default(resolvable.field)
    else:
        raise ResolutionError("No value provided and parameter has no default")
