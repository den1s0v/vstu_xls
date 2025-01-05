from collections import defaultdict

from constraints_2d.BoolExpr import BoolExpr
# from constraints_2d.CoordVar import CoordVar
from geom2d import Box


class SpatialConstraint(BoolExpr):
    """ Пространственное ограничение
        для проверки взаимного расположения двумерных объектов. """

    @classmethod
    def get_kind(cls):
        return "Base SpatialConstraint"

    component_name_aliases = {
        'this': '',
        'parent': '_',
    }

    def replace_vars(self, var_mapping: dict[str, int | str]):
        """ Change variables in-place """
        raise NotImplementedError(type(self))

    def eval_with_components(self, component2box: dict[str, Box]) -> bool:
        var_name2value = self._map_vars_to_component_coordinates(component2box)
        return self.eval(var_name2value)

    def referenced_components(self) -> set[str]:
        components = {var.component for var in self.referenced_variables()}
        return components

    def referenced_components_with_attributes(self) -> dict[str, list[str]]:
        component2attrs = defaultdict(list)
        for var in self.referenced_variables():
            attr4box = var.attr_for_box()
            attr_list = component2attrs[var.component]
            if attr4box not in attr_list:
                attr_list.append(attr4box)
                attr_list.sort()
        return dict(component2attrs)

    def inline_component_positions(self, component2box: dict[str, Box]):
        var_name2value = self._map_vars_to_component_coordinates(component2box)
        self.replace_vars(var_name2value)
        return self

    def replace_components(self, mapping: dict[str, str]):
        """ Rename variables — change leading parts of variables so these denote different components. In-place. """
        vars_mapping = self._vars_mapping_for_replacing_components(mapping)
        self.replace_vars(vars_mapping)
        return self

    def _fit_component_mapping(self, mapping: dict[str, object]):
        """ Update mapping to utilize component_name_aliases to existing components if required """
        this_components = self.referenced_components()
        components_requested = set(mapping.keys())
        unmatched_components = components_requested - this_components

        if unmatched_components:
            known_aliases = set(self.component_name_aliases.keys())
            unknown_components = unmatched_components - known_aliases
            assert not unknown_components, f"Cannot map components {unknown_components} on expression `{self}`."

            for name in unmatched_components & known_aliases:
                alias = self.component_name_aliases[name]
                # replace key in given mapping
                mapping[alias] = mapping[name]
                del mapping[name]

        return mapping

    def _vars_mapping_for_replacing_components(self, component_mapping: dict[str, str]):
        component_mapping = self._fit_component_mapping(component_mapping)
        var_names_mapping = {}
        for v in self.referenced_variables():
            if v.component in component_mapping:
                target_component = component_mapping[v.component]
                new_var = v.clone()
                new_var.component = target_component  # change `component` in the copy
                var_names_mapping[v.var_name] = new_var.var_name
        return var_names_mapping

    def _map_vars_to_component_coordinates(self, component2box: dict[str, Box]) -> dict[str, int]:
        component2box = self._fit_component_mapping(component2box)
        var_name2value = {}
        for v in self.referenced_variables():
            if v.component in component2box:
                box = component2box[v.component]
                try:
                    value = getattr(box, v.attr_for_box())
                except AttributeError:
                    raise AttributeError(v, v.attr, f'Cannot read {v.attr} from Box instance.')
                var_name2value[v.var_name] = value
        return var_name2value
