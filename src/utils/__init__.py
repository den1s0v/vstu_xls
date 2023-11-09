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
