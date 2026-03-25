# grammar2d.py

# from grammar2d import PatternComponent, Pattern2d, NonTerminal
from vstuxls.grammar2d.AreaPattern import AreaPattern
from vstuxls.grammar2d.ArrayInContextPattern import ArrayInContextPattern
from vstuxls.grammar2d.ArrayPattern import ArrayPattern
from vstuxls.grammar2d.Grammar import Grammar, read_grammar
from vstuxls.grammar2d.GrammarMatcher import GrammarMatcher

# from grammar2d.Match2d import Match2d  # still tries to load module, not class, when importing from grammar2d...
from vstuxls.grammar2d.NonTerminal import NonTerminal
from vstuxls.grammar2d.Pattern2d import Pattern2d, PatternRegistry
from vstuxls.grammar2d.PatternComponent import PatternComponent
from vstuxls.grammar2d.Terminal import Terminal

# Note: all these imports are required since classed must be registered.
