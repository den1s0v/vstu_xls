# grid.py

from abc import ABC, abstractmethod
# from weakref import WeakValueDictionary

from adict import adict

from geom2d import Point, Box, Size
from geom2d import *


# Данные 2D-сетки.

class Grid(ABC):
    """
        Двумерная сетка/решётка ограниченных размеров.
        Сама "матрица" с чистыми данными, без их интерпретации.
    """
    point2cell: dict

    def __init__(self) -> None:
        self.point2cell = dict()
        self._bb_cache = None

    def _clear_cells(self) -> None:
        self.point2cell.clear()

    def registerCell(self, cell: 'Cell') -> None:
        """ Запомнить ссылку на ячейку (или, если она объединённая, ссылки на ячейку из всех кооррдинат внутри неё) """
        for point in cell.box.iterate_points():
            self.point2cell[point] = cell
        # super().__init__()

    def getCell(self, point: Point) -> Optional['Cell']:
        return self.point2cell.get(point)

    def getBoundingBox(self, force_recalc = False) -> Box:
        """ Размеры эффективной области расположения данных (за пределами этой области могут быть только пустые ячейки). 
            Default implementation that can be improved by subclasses.
        """
        if not self._bb_cache or force_recalc:
            boxes = [cell.box for cell in self.point2cell.values()]
            l = min(box.left   for box in boxes)
            r = max(box.right  for box in boxes)
            t = min(box.top    for box in boxes)
            b = max(box.bottom for box in boxes)
            self._bb_cache = Box.from_2points(l, t, r, b)
        return self._bb_cache
    
    def getView(self, box: Box = None) -> Optional['GridView']:
        """Проекция заданной области внутри сетки или всей сетки целиком."""
        boundingBox = self.getBoundingBox()
        box = box.intersect(boundingBox) if box else boundingBox
        return GridView(self, box)

    def supportsCellMerging(self) -> bool:
        return False
    
    
class GridWithCellMerging(Grid):
    """
        Двумерная сетка/решётка ограниченных размеров.
        Допустимо объединение прямоугольных областей в целые ячейки.
    """
    def supportsCellMerging(self) -> bool:
        return True
    



class Cell:
    """ Ячейка 2D-матрицы, содержащая текст. Обычно размером 1x1, но может быть задана и больше посредством поля size. """
    def __init__(self, grid: Grid, point: Point, size:Size=None, content = '', style = None):
        self.grid = grid
        self.point = point
        self.size = size or Size(1, 1)
        self.content = content
        self.style = style

    @property
    def box(self) -> Box:
        return Box(*self.point, *self.size)

    def __str__(self) -> str:
        return '%s@%s' % (repr(self.content), str(self.box))


class CellStyle:
    font_style: set
    background_color: str
    borders: set
    pass



# Проекция 2D-сетки.

class Region(Box):
    """ Проекция определённой области (региона) 2D-сетки. Может хранить дополнительные данные о регионе в поле data """
    def __init__(self, grid_view: 'GridView', box: Box) -> None:
        super().__init__(*box)
        self.grid_view = grid_view
        self.data = adict()

    # def __new__(cls, grid_view: 'GridView', box: Box):
    #     return super(Region, cls).__new__(cls, grid_view, box=box)

    def getCell(self, point) -> Optional['CellView']:
        if point not in self:
            return None  # не показывать ничего за пределами области проекции.
        return self.grid_view.getCell(point)

    def getRegion(self, box) -> Optional['Region']:
        if not (box in self or
                box.overlaps(self) and (box := box.intersect(self)) and box):
            return None  # не показывать ничего за пределами области проекции.
        return self.grid_view.getRegion(box)
        
    def iterateCells(self, directions = (RIGHT, DOWN)):
        """ Yield all non-empty cells within this region.

        Args:
            directions (tuple, optional): Directions of traversal for main & secondary loop over 2D area. Second element of the 2-tuple may be omitted. Defaults to (RIGHT, DOWN).

        Yields:
            Point: non-empty cell within this region
        """
        for point in self.iterate_points(directions):
            cw = self.getCell(point)
            if cw:
                yield cw

    def findCell(self, predicate: callable, directions = (RIGHT, DOWN)) -> Optional['CellView']:
        """ Найти первую ячейку, удовлетворяющую условию `predicate`. Перебор осуществляется в заданных направлениях.
            Find the first cell that satisfies the `predicate` condition. The search is carried out in a given `directions`. 
            `predicate` should take CellView as the only argument and return bool.
            """
        for cw in self.findAllCells(predicate, directions):
            return cw
        return None

    def findAllCells(self, predicate: callable, directions = (RIGHT, DOWN)):
        for cw in self.iterateCells(directions):
            if predicate(cw):
                yield cw

    def lookOutside(self, direction: Direction, distance: int = -1) -> 'Region':
        """ Получить регион, снаружи примыкающий к этому с заданной стороны и протяжённый на заданное расстояние (по умолчанию до границы проекции решетки).
        Get a region that is externally adjacent to this one from a given side and extended by a given distance (by default to the border of the grid_view).

        Args:
            direction (_type_): direction that determines target side.
            distance (int, optional): length of region along `direction`. Values below zero mean maximum possible length. Defaults to -1.

        Returns:
            Region: new non-overlapping Region having the same adjacent side to this one.
        """
        side = self.get_side_dy_direction(direction)
        if distance >= 0:
            end = side + distance * direction.coordinate_sign
        else:
            end = self.grid_view.get_side_dy_direction(direction)
            
        if direction.is_horizontal:
            coords = side, end, self.top, self.bottom
        else:
            coords = self.left, self.right, side, end

        return Box.from_2points(*coords)




class CellView(Region):
    # Проекция одной ячейки 2D-сетки. Может хранить дополнительные данные о ячейке в поле data.
    def __init__(self, grid_view: 'GridView', cell: Cell) -> None:
        super().__init__(grid_view, cell.box)
        self.cell = cell
        
    def __str__(self) -> str:
        return str(self.cell)


class GridView(Region):
    """ Проекция всей 2D-сетки (grid). Проекция может хранить дополнительные данные о ячейках и регионах (в соответствующих объектах проекций). 
        Предполагается, что сама grid не будет изменяться после создания GridView для неё.
    """
    grid: Grid
    cell_cache: dict[Point, CellView]
    region_cache: dict[Point, Region]

    def __init__(self, grid: Grid, box: Box) -> None:
        super().__init__(self, box)  # Note. `self` here is meaningful param for Region's constructor.
        self.grid = grid
        self.cell_cache = dict()  # WeakValueDictionary()
        self.region_cache = dict()  # WeakValueDictionary()
        
    def getCell(self, point: Point) -> Optional['CellView']:
        if point not in self:
            return None  # не показывать ничего за пределами области проекции.

        cw = self.cell_cache.get(point, False)  # False: not in the cache, None: cached empty cell.
        if cw:
            return cw
        if cw is False:
            cell = self.grid.getCell(point)
            if cell:
                if (not self.grid.supportsCellMerging() or point == cell.point):
                    cw = CellView(self, cell)

                else:  # `cell.point` may differ from requested `point` for a merged cell.
                    # Ячейка есть, но её начало не здесь.
                    cw = self.cell_cache.get(cell.point)
                    if not cw:
                        # Создадим проекцию на фактическом расположении ячейки.
                        cw = CellView(self, cell)
                        self.cell_cache[cell.point] = cw

                # Запомним проекцию ячейки: там, откуда мы ячейку запрашивали.
                self.cell_cache[point] = cw
                return cw
            
            else:
                # В этой точке нет ячейки, запомним это.
                self.cell_cache[point] = None
        return None
        
    def getRegion(self, box: Box) -> Optional['Region']:
        if not (box in self or
                box.overlaps(self) and (box := box.intersect(self)) and box):
            return None  # не показывать ничего за пределами области проекции.
        
        rg = self.region_cache.get(box)
        if not rg:
            rg = Region(self, box)
            self.region_cache[box] = rg

        return rg
