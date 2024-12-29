import math
import re

from string_matching.StringTransformer import StringTransformer


_RE_SEVERAL_SPACES = re.compile(r'\s{2,}')
_RE_SPACES = re.compile(r'\s+')
_RE_GAPS = re.compile(r'\b\s+\b')
_RE_HYPEN_SPACED = re.compile(r'\s*-\s*')




# Подкласс для преобразования строк
class Decode_re_spaces_Transformer(StringTransformer):
    """
    Перечень замен:
    ' '  -> \\s* -- Один пробел становится "опциональным пробелом",
    "  " -> \\s+ -- Два пробела становятся "минимум одним пробелом",
    "   " -> " " -- Три пробела становятся просто одним пробелом.
    """
    @classmethod
    def get_id(cls):
        return "decode_re_spaces"

    def transform(self, re_spaces: str):
        return (re_spaces
                .replace("   ", r'\s')
                .replace("  ", r'\s+')
                .replace(" ", r'\s*'))
    
StringTransformer.register(Decode_re_spaces_Transformer)



def shrink_extra_inner_spaces(string: str):
    return _RE_SEVERAL_SPACES.sub(" ", string)
    

# Подкласс для преобразования строк
class shrink_extra_inner_spaces_Transformer(StringTransformer):
    """ Replace each sequence of several whitespaces with one space. """
    @classmethod
    def get_id(cls):
        return "shrink_extra_inner_spaces"

    def transform(self, string: str):
        return shrink_extra_inner_spaces(string)
    
StringTransformer.register(shrink_extra_inner_spaces_Transformer)




def fix_sparse_words(string: str, _mul_of_longest_as_sep=2, _min_spaces=5):
    """ Try fix:
     'М А Т Е М А Т И К А' -> 'МАТЕМАТИКА'
     'И Н.   Я З Ы К' -> 'ИН. ЯЗЫК' (note: keep space between words)
     """
    # if string.count(' ') < _min_spaces:
    # if len(gap_ms := _RE_GAPS.findall(string)) < _min_spaces:
    spaces_count = string.count(" ")
    if spaces_count == 0 or spaces_count * 2 < len(string) - 1:
        # not enough spaces to apply this transformation
        return string
    gaps = {len(s) for s in _RE_GAPS.findall(string)}

    if not gaps:
        return string

    gaps = sorted(gaps)
    # min_gap, max_gap = min(gaps), max(gaps)
    min_gap = min(gaps)

    # TODO: min_gap = 0, если слова без разрывов (???)

    # separator_min_len = max(min_gap + 1, math.ceil(max_gap - (_frac_of_longest_as_sep or 0.5) * (max_gap - min_gap)))
    separator_min_len = math.ceil(_mul_of_longest_as_sep * min_gap)

    words = string.split(" " * separator_min_len)
    # remove spaces from each word
    words = [_RE_SPACES.sub('', w) for w in words]
    # filter empty words (if any), before joining words back
    return " ".join(w for w in words if w)



# Подкласс для преобразования строк
class fix_sparse_words_Transformer(StringTransformer):
    """ Try fix words formatted to look wide with spaces between chars, e.g.:
     'М А Т Е М А Т И К А' -> 'МАТЕМАТИКА'
     'И Н.   Я З Ы К' -> 'ИН. ЯЗЫК' (note: keep the space between words)
     """
    @classmethod
    def get_id(cls):
        return "fix_sparse_words"

    def transform(self, string: str):
        return fix_sparse_words(string)
    
StringTransformer.register(fix_sparse_words_Transformer)



# Подкласс для преобразования строк
class remove_all_spaces_Transformer(StringTransformer):
    """ Remove all spaces from string.
     """
    @classmethod
    def get_id(cls):
        return "remove_all_spaces"

    def transform(self, string: str):
        return string.replace(" ", '')
    
StringTransformer.register(remove_all_spaces_Transformer)



# Подкласс для преобразования строк
class remove_spaces_around_hypen_Transformer(StringTransformer):
    """ Remove all spaces from string.
     """
    @classmethod
    def get_id(cls):
        return "remove_spaces_around_hypen"

    def transform(self, string: str):
        return _RE_HYPEN_SPACED.sub("-", string)
    
StringTransformer.register(remove_spaces_around_hypen_Transformer)


