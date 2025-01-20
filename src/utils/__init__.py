from contextlib import contextmanager
from pathlib import Path
from timeit import default_timer as timer

from adict import adict


class Checkpointer:
    """Measures time between hits. Requires the `from timeit import default_timer as timer`"""

    def __init__(self, start=True):
        super().__init__()
        self.first = timer()
        self.last = self.first
        # if start:
        #     self.hit()

    def reset_now(self):
        self.__init__(start=False)

    def hit(self, label=None) -> float:
        now = timer()
        delta = now - self.last
        if label:
            print((label or 'Checkpoint') + ':', "%.4f" % delta, 's')
        self.last = now
        return delta

    def since_start(self, label=None, hit=False) -> float:
        now = timer()
        delta = now - self.first
        if label:
            print(label or 'Total:', "%.4f" % delta, 's')
        if hit:
            self.last = now
        return delta


def reverse_if(iterable, reverse=True):
    """ Return `reversed(iterable)` if `reverse==True`, and untouched `iterable` otherwise.
    """
    if reverse:
        return reversed(iterable)
    return iterable


@contextmanager
def global_var(**kwargs):
    """ Declare a global var for usage within context block.
    This is not thread-safe.
    Usage example:
    print(foo)  # NameError: name 'foo' is not defined

    with global_vars(foo='bar'):
        ...
        print(foo)  # prints 'bar'
        ...
        with global_vars(foo='BAZ'):
            print(foo)  # prints 'BAZ'
        ...
        print(foo)  # prints 'bar'
        ...

    print(foo)  # NameError: name 'foo' is not defined
    """
    # setup: back up previous values of global variables, if set.
    glob = globals()  # updatable dict of global variables
    prev_values = {}
    for name, new_value in kwargs.items():
        if name in glob:
            prev_values[name] = glob[name]
        glob[name] = new_value
    try:
        yield
    finally:
        # cleanup: restore previous values or delete used variables.
        for name in kwargs.keys():
            if name in prev_values:
                glob[name] = prev_values[name]
            elif name in glob:  # if it was not deleted within wrapped code
                del glob[name]


class safe_adict(adict):
    """Same as `adict` but `__getattr__` behaves as `dict.get`, i.e. `None` is just returned if a key is absent."""

    def __getattr__(self, name):
        # don't throw any exception on key absence
        return self.get(name)


class WithCache:
    """ Mixin that adds `self._cache` attribute to object (on demand, not in constructor).
    type: adict, i.e. ordinary dict but allowing access to a key as an attr."""

    @property
    def _cache(self) -> safe_adict:
        if not hasattr(self, '_cache_d'):
            self._cache_d = safe_adict()
        return self._cache_d


class WithSafeCreate:
    """ Mixin that adds to a class `cls.safe_create` method
     that filters incompatible kwargs, i.e. not defined as-level class attributes.
     Also, `cls.filter_init_kwargs` method is added.
     """

    @classmethod
    def filter_init_kwargs(cls, kwargs: dict) -> dict:
        valid_args = set(cls.__annotations__.keys())
        for base in cls.mro():
            try:
                valid_args |= set(base.__annotations__.keys())
            except AttributeError:
                pass

        kwargs_filtered = {
            k: val
            for k, val in kwargs.items()
            if k in valid_args
        }
        return kwargs_filtered

    @classmethod
    def safe_create(cls, **kwargs) -> 'new cls':
        """ Class method to be used with dataclasses
        instead of direct instance creation
        to avoid `Unknown/unsupported keyword argument` errors in a smart way. """
        return cls(**cls.filter_init_kwargs(kwargs))


def find_file_under_path(rel_path: 'str|Path', *directories, search_up_steps=3) -> Path | None:
    if not directories:
        # use current dir
        directories = (Path('.'), )

    for up_dirs in range(0, search_up_steps):
        for directory in directories:
            base = Path(directory).resolve()
            for _ in range(up_dirs):
                base = base.parent
            p = Path(base, rel_path)
            if p.exists():
                return p.resolve()

    return None


