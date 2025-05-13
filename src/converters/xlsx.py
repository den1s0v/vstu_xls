from openpyxl.worksheet.worksheet import Worksheet

from converters.abstract import AbstractGridBuilder
from geom2d.point import Point
from geom2d.size import Size
from grid import Cell, CellStyle, Grid


class ExcelGrid(Grid, AbstractGridBuilder):
    """A Grid implementation that builds a model from an Excel worksheet using openpyxl.
    Stores references to original openpyxl cells for style and formatting access."""

    def __init__(self, worksheet: Worksheet) -> None:
        super().__init__()
        self._worksheet = worksheet
        self._load_cells(worksheet)

    def _load_cells(self, data: Worksheet) -> None:
        """Load cells from the provided worksheet, creating Cell objects and storing openpyxl cell references."""
        # Iterate through all cells in the worksheet's defined dimensions
        for row in data.iter_rows(
            min_row=1, max_row=data.max_row, min_col=1, max_col=data.max_column
        ):
            for excel_cell in row:
                if excel_cell.value is None:
                    continue  # Skip empty cells

                x = excel_cell.column
                y = excel_cell.row

                # Create CellStyle from openpyxl cell properties
                style = self._create_cell_style(excel_cell)

                # Create Cell with content and style
                cell = Cell(
                    grid=self,
                    point=Point(x, y),
                    size=Size(1, 1),  # Default size; merged cells handled below
                    content=str(excel_cell.value),
                    style=style,
                )

                # Store reference to original openpyxl cell in cell.data
                cell.data = {"openpyxl_cell": excel_cell}

                # Register the cell
                self.registerCell(cell)

        # Handle merged cells
        self._process_merged_cells()

    def _create_cell_style(self, excel_cell) -> CellStyle:
        """Create a CellStyle object from openpyxl cell properties."""
        style = CellStyle()

        # Initialize style attributes
        style.font_style = set()
        style.borders = set()
        style.background_color = None

        # Font styles
        if excel_cell.font:
            if excel_cell.font.b:
                style.font_style.add("bold")
            if excel_cell.font.i:
                style.font_style.add("italic")
            if excel_cell.font.u:
                style.font_style.add("underline")

        # Border styles
        if excel_cell.border:
            if excel_cell.border.left and excel_cell.border.left.style:
                style.borders.add("left")
            if excel_cell.border.right and excel_cell.border.right.style:
                style.borders.add("right")
            if excel_cell.border.top and excel_cell.border.top.style:
                style.borders.add("top")
            if excel_cell.border.bottom and excel_cell.border.bottom.style:
                style.borders.add("bottom")

        # Background color (convert RGB to hex if present)
        if excel_cell.fill and excel_cell.fill.fgColor and excel_cell.fill.fgColor.type == "rgb":
            style.background_color = excel_cell.fill.fgColor.rgb

        return style

    def _process_merged_cells(self) -> None:
        """Process merged cell ranges, updating Cell objects with appropriate sizes."""
        if not self._worksheet.merged_cells:
            return

        for merged_range in self._worksheet.merged_cells.ranges:
            min_col, min_row, max_col, max_row = (
                merged_range.min_col,
                merged_range.min_row,
                merged_range.max_col,
                merged_range.max_row,
            )

            x, y = min_col, min_row
            point = Point(x, y)

            # Calculate size of the merged cell
            width = max_col - min_col + 1
            height = max_row - min_row + 1
            size = Size(width, height)

            # Get the top-left cell from point2cell
            cell = self.getCell(point)
            if not cell:
                # Create a new cell if none exists (e.g., empty merged cell)
                excel_cell = self._worksheet.cell(row=min_row, column=min_col)
                style = self._create_cell_style(excel_cell)
                cell = Cell(
                    grid=self,
                    point=point,
                    size=size,
                    content=str(excel_cell.value or ""),
                    style=style,
                )
                cell.data = {"openpyxl_cell": excel_cell}
            else:
                # Update existing cell's size
                cell.size = size

            # Clear any other cells in the merged range and ensure they point to the top-left cell
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    if row == min_row and col == min_col:
                        continue  # Skip the top-left cell
                    point = Point(col - 1, row - 1)
                    if point in self.point2cell:
                        del self.point2cell[point]
                    self.point2cell[point] = cell

            # Re-register the cell to update point2cell mappings
            self.registerCell(cell)

    def supportsCellMerging(self) -> bool:
        """ExcelGrid supports merged cells."""
        return True
