from contextlib import contextmanager
from timeit import default_timer as timer


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
def global_vars(**kwargs):
    """ Declare a global var for usage within context block.
    Usage:
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

