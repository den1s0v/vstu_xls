# grammar2d.py

from grammar2d import PatternComponent, GrammarElement, NonTerminal
from grammar2d.Grammar import Grammar
from grammar2d.GrammarElement import GrammarElement
from grammar2d.NonTerminal import NonTerminal
from grammar2d.PatternComponent import PatternComponent
from grammar2d.Terminal import Terminal

GRAMMAR: 'Grammar' = None


class StructureElement(NonTerminal):
    ...


class ArrayElement(NonTerminal):
    ...


