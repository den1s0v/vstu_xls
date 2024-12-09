# constraints_2d

from constraints_2d.SpatialConstraint import SpatialConstraint

from constraints_2d.utils.sympy_expr import SympyExpr, register_sympy_as_expr_backend

# Note: global code (runs once all classes have initialized)
register_sympy_as_expr_backend()  # this registers subclass of SpatialConstraint



# TODO: refactor as static methods of SpatialConstraint ??
def trivial_constraints_for_box(component_name: str) -> SpatialConstraint:
    comp = component_name
    return SpatialConstraint(f"""
            {comp}_left + {comp}_w == {comp}_right  and
            {comp}_left < {comp}_right  and
            {comp}_top  + {comp}_h == {comp}_bottom  and
            {comp}_top  < {comp}_bottom
                             """.strip().replace('\n', ''))

def constraints_for_box_inside_container(component_name: str, container_name: str) -> SpatialConstraint:
    comp = component_name
    outer = container_name
    return SpatialConstraint(f"""
            {outer}_left <= {comp}_left  and
            {outer}_top  <= {comp}_bottom  and
            {comp}_right <= {outer}_right  and
            {comp}_bottom <= {outer}_bottom
                             """.strip().replace('\n', ''))









# \\\\\\\\\\\\\\\\\\

# relations_2d.py

""" Пространственные взаимоотношения двумерных прямоугольных структур. """


"""

Экземпляр взаимоотношения связывает описание элементов для спецификации 2D-грамматики.



○ Relation2d  # Взаимоотношение элементов
  |
  ○ Item  # Элемент, компонент.
  |
  ○ Aggregation  # Включающее отношение. Агрегация содержит элементы, находящиеся в общих рамках.
  | |
  | ○ Structure  # содержит именованные элементы (которые не пересекаются)
  | |
  | ○ Collection  #  содержит однотипные элементы (которые не пересекаются)
  |  |
  |  ○ Array  # ← элементы коллекции пространственно упорядочены
  |    |
  |    ○ LineArray  # Ряд — горизонтальный либо вертикальный
  |    ○ FillArray  # связная область "заливки" элементами / AdjacentCellsArea
  |
  |
  ○ Ousting  # Взаимное вытеснение (всех элементов)
  ○ Opposition  # Сопоставление на удалении (друг напротив друга)
  ○ Intersection  # Комбинация пересечением

"""

