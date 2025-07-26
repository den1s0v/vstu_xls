import unittest

from tests_bootstrapper import init_testing_environment

init_testing_environment()

from pathlib import Path

from utils import find_file_under_path
from grammar2d import read_grammar

from grammar2d.PatternComponent import PatternComponent
from constraints_2d.LocationConstraint import LocationConstraint
from geom2d import Box, RangedBox
from geom2d import Direction, open_range, RangedSegment
from grammar2d.Match2d import Match2d
from grammar2d.Pattern2d import Pattern2d



class UtilsTestCase(unittest.TestCase):
    def test_find_file_under_path_1(self):
        source_path = '../cnf/cell_types.yml'
        expected_path = Path(source_path).resolve()

        resolved_path = find_file_under_path(source_path, '../cnf/grammar_root.yml')

        self.assertIsNotNone(resolved_path)
        self.assertEqual(expected_path, resolved_path)

    def test_find_file_under_path_2(self):
        source_path = 'cnf/cell_types.yml'
        expected_path = Path('./../', source_path).resolve()

        resolved_path = find_file_under_path(source_path, '../cnf/grammar_root.yml')

        self.assertIsNotNone(resolved_path)
        self.assertEqual(expected_path, resolved_path)

    def test_find_file_under_path_3(self):
        source_path = 'cell_types.yml'
        expected_path = Path('./../cnf/', source_path).resolve()

        resolved_path = find_file_under_path(source_path, '../cnf/grammar_root.yml')

        self.assertIsNotNone(resolved_path)
        self.assertEqual(expected_path, resolved_path)


class GrammarTestCase(unittest.TestCase):
    def test_1(self):

        grammar = read_grammar()
        print()
        print(grammar)

        from pprint import pprint
        pprint(grammar.cell_types)
        pprint(grammar.patterns)

    # Test cases for get_ranged_box_for_parent_location
    def test_get_ranged_box_for_parent_location_inner(self):

        # Example 1: {location: left}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[LocationConstraint(side_to_gap={'left': open_range(0, 0)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=(20, '40+'),
                             ry=('1-', '5+'))
        self.assertEqual(expected, result)

        #
        # Example 2: {location: {}}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[]
        )
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('20-', '40+'),
                             ry=('1-', '5+'))
        self.assertEqual(expected, result)

        #
        # Example 3: {location: left, right, bottom}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[
                LocationConstraint(side_to_gap={
                    'left': open_range(0, 0),
                    'right': open_range(0, 0),
                    'bottom': open_range(0, 0)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=(20, 40),
                             ry=('1-', 5))
        self.assertEqual(expected, result)

        #
        # Example 4: {location: right, bottom}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[
                LocationConstraint(side_to_gap={
                    'right': open_range(0, 0),
                    'bottom': open_range(0, 0)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('20-', 40),
                             ry=('1-', 5))
        self.assertEqual(expected, result)

        #
        # Example 5: {location: top: 0, left: '0..1', right: '0..2'}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[
                LocationConstraint(side_to_gap={
                    'top': open_range(0, 0),
                    'left': open_range(0, 1),
                    'right': open_range(0, 2)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('19..20', '40..42'),
                             ry=(1, '5+'))
        self.assertEqual(expected, result)

        #
        # Example 6: {location: top: -2, right: '-3..3'}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[
                LocationConstraint(side_to_gap={
                    'top': open_range(-2, -2),
                    'right': open_range(-3, 3)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('*..20', '37..43'),
                             ry=(3, '5+'))
        self.assertEqual(expected, result)

        #
        # Example 7: {location: top: '*', left: '*', right: '*', bottom: '*'}
        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=True,
            constraints=[
                LocationConstraint(side_to_gap={
                    'top': open_range(None, None),
                    'left': open_range(None, None),
                    'right': open_range(None, None),
                    'bottom': open_range(None, None)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('*', '*'),
                             ry=('*', '*'))
        self.assertEqual(expected, result)

    def test_get_ranged_box_for_parent_location_inner_3x3(self):

        #
        m_box = RangedBox(rx=(2, 3), ry=(1, 2)).to_box()
        self.assertEqual(Box(2,1, 1,1), m_box)
        component_match = Match2d(box=m_box, pattern="dummy str instead of pattern")

        pattern_component = PatternComponent(
            name="child", pattern="child_pattern", inner=True,
            constraints=[
                LocationConstraint(side_to_gap={
                    # {left: 0, top: 1, bottom: 1}
                    'top': open_range(1, 1),
                    'left': open_range(0, 0),
                    'right': open_range(0, None),
                    'bottom': open_range(1, 1)})])
        """  |¯ ¯ ¯~
             |◘    ~
             |_ _ _~   """
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=(2, '3+'),
                             ry=(0, 3))
        self.assertEqual(expected, result)

    def test_get_ranged_box_for_parent_location_outer(self):

        component_match = Match2d(box=RangedBox(rx=(20, 40), ry=(1, 5)).to_box(), pattern="dummy str instead of pattern")

        # Example 1: {location: left}
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[LocationConstraint(check_implicit_sides=False, side_to_gap={'left': open_range(0, None)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('40+', '*'),
                             ry=('*', '*'))
        self.assertEqual(expected, result)

        #
        # Example 2: {location: {}}
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('*', '*'),
                             ry=('*', '*'))
        self.assertEqual(expected, result)

        #
        # Example 3: {location: left: 7}
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[LocationConstraint(check_implicit_sides=False, side_to_gap={'top': open_range(7, 7)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('*', '*'),
                             ry=(12 ,'*'))
        self.assertEqual(expected, result)

        #
        # Example 4: {location: top: '0..2', left: '0-', right: '0-'}
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[
                LocationConstraint(check_implicit_sides=False, side_to_gap={
                    'top': open_range(0, 2),
                    'left': open_range(None, 0),
                    'right': open_range(None, 0)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(
            rx=RangedSegment.make(
                ('40-', '20+'),
                validate=False),
            ry=RangedSegment.make(
                ('5..7', '*'),
                validate=False))
        self.assertEqual(expected, result)

        #
        # Example 5: {location: right}
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[
                LocationConstraint(check_implicit_sides=False, side_to_gap={'right': open_range(0, None)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('*', '20-'),
                             ry=('*', '*'))
        self.assertEqual(expected, result)

        #
        # Example 6: {location: right: '3..10'}
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[
                LocationConstraint(check_implicit_sides=False, side_to_gap={'right': open_range(3, 10)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(rx=('*', '10..17'),
                             ry=('*', '*'))
        self.assertEqual(expected, result)

        #
        # Example 7: {location: top: '1-', bottom: '1-' }
        pattern_component = PatternComponent(
            name="child",
            pattern="child_pattern",
            inner=False,
            constraints=[
                LocationConstraint(check_implicit_sides=False, side_to_gap={
                    'top': open_range(None, -1),
                    'bottom': open_range(None, -1)})])
        result = pattern_component.get_ranged_box_for_parent_location(component_match)
        expected = RangedBox(
            rx=RangedSegment.make(
                ('*', '*'),
                validate=False),
            ry=RangedSegment.make(
                ('4-', '2+'),
                validate=False))
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
    # GrammarTestCase.test_1(...)
