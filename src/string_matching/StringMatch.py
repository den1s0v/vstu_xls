import re
from dataclasses import dataclass


# Circular import workaround: https://stackoverflow.com/a/17229804/12824563
import string_matching.StringPattern as ns


@dataclass
class StringMatch:
    re_match: re.Match | list[str]
    pattern: 'ns.StringPattern'
    text: str

    @property
    def confidence(self) -> float:
        return self.pattern.confidence

    @property
    def covered(self) -> int:
        """ Length of `match` """
        return len(self.re_match[0])

    @property
    def coverage_ratio(self) -> float:
        """ Returns result of division: (Length of `match`) / (Length of `text`).
        If `text` is empty, returns 1. If match is empty with non-empty `text`, returns 0. 
        """
        text_len = len(self.text)
        return self.covered / text_len if text_len > 0 else 1

    @property
    def precision(self) -> float:
        """ Precision of `match` in range [0..1] usually derived from pattern's confidence & match coverage. """
        return self.pattern.calc_precision_of_match(self)

    def __contains__(self, index_or_name: int | str):
        """ Has a group / capture index """
        match_index = self.pattern.logical_index_to_re_group_index(self.re_match, index_or_name)
        return match_index is not None

    def group(self, index_or_name: int | str) -> str|None:
        """ Get matched substring for a capturing group determined by name or number (1-based index) """
        match_index = self.pattern.logical_index_to_re_group_index(self.re_match, index_or_name)
        return self.re_match[match_index] if match_index is not None else None

    __getitem__ = group

    def __str__(self) -> str:
        return f"<StringMatch groupdict: {self.groupdict()} on text={repr(self.text)}>"

    __repr__ = __str__

    def groupdict(self) -> dict:
        """ All captured groups, by names, or by indices if captures not defined. """
        if self.pattern.captures:
            return {
                name: self[name]
                for name in self.pattern.captures
            }

        elif isinstance(self.re_match, re.Match):
            # Join positional & named groups from re.Match
            return dict(
                enumerate(self.re_match.groups(), start=1)  # index groups as 1-based
            ) | self.re_match.groupdict()

        elif isinstance(self.re_match, list):
            lst = self.re_match
            return {
                k + 1: v  # re-index to 1-based
                for k, v in enumerate(lst)
                if k != 0  # Hide 0 group as re.Match does.
            }

        return {}  # Cannot obtain valid dict data. TODO: raise?
