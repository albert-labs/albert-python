from __future__ import annotations

from enum import Enum
from typing import Any, ForwardRef, Literal, TypedDict, Union

import pandas as pd
from pydantic import Field, PrivateAttr, field_validator, model_validator, validate_call

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import DataColumnId, InventoryId
from albert.core.shared.models.base import BaseResource, BaseSessionResource
from albert.core.shared.models.patch import PatchDatum
from albert.exceptions import AlbertException, AlbertHTTPError
from albert.resources.inventory import InventoryItem

# Define forward references
Row = ForwardRef("Row")
Column = ForwardRef("Column")
Sheet = ForwardRef("Sheet")

CellAttributeValue = str | float | int | dict[str, Any] | list[Any] | None


class CellChangeId(TypedDict):
    """Internal identifier (row ID and column ID) locating a cell in a change payload."""

    rowId: str
    colId: str


class CellChangePayload(TypedDict):
    """Internal payload describing the patch operations to apply to a single cell."""

    Id: CellChangeId
    data: list[PatchDatum]


class CellColor(str, Enum):
    """A background color that can be applied to Sheet cells.

    Each value is the RGB string the platform stores for the cell background.
    Used with :meth:`Column.recolor_cells` and :meth:`Row.recolor_cells` to
    highlight cells in a Sheet.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.sheets import CellColor
        column = sheet.get_column(column_name="Formulation A")
        column.recolor_cells(CellColor.GREEN)
        ```
    """

    WHITE = "RGB(255, 255, 255)"
    RED = "RGB(255, 161, 161)"
    GREEN = "RGB(130, 222, 198)"
    BLUE = "RGB(214, 233, 255)"
    YELLOW = "RGB(254, 240, 159)"
    ORANGE = "RGB(255, 227, 210)"
    PURPLE = "RGB(238, 215, 255)"


class CellType(str, Enum):
    """The kind of content a Cell, Column, or Row holds.

    Cells, Columns, and Rows all carry a type drawn from this enum, which
    determines how the platform interprets their contents. The values most
    relevant when building formulations are ``INVENTORY`` (an ingredient amount),
    ``TOTAL`` (a computed total row), ``FORMULA`` and ``FOR`` (formulation
    columns), ``LKP`` (a lookup that displays an inventory attribute), and
    ``BLANK`` (an empty cell). The remaining members correspond to specialized
    grid content such as tags, prices, tasks, results, and apps.
    """

    INVENTORY = "INV"
    APP = "APP"
    BLANK = "BLK"
    FORMULA = "Formula"
    TAG = "TAG"
    PRICE = "PRC"
    PDC = "PDC"
    BAT = "BAT"
    TOTAL = "TOT"
    TAS = "TAS"
    DEF = "DEF"
    LKP = "LKP"
    FOR = "FOR"
    EXTINV = "EXTINV"
    BTI = "BTI"
    PRM = "PRM"
    PRG = "PRG"
    RSL = "RSL"
    FNC = "FNC"
    WFL = "WFL"
    DAC = "DAC"
    INT = "INT"
    DAT = "DAT"
    NDR = "NDR"
    PIC = "PIC"


class DesignType(str, Enum):
    """The section of a Sheet that a Design represents.

    A Sheet is organized into stacked sections, each backed by a Design
    (:class:`Design`). The type identifies which section:

    - ``PRODUCTS`` — Product Design, where formulations are built.
    - ``PROCESS`` — Process Design.
    - ``RESULTS`` — Results, holding Property Tasks and their data.
    - ``APPS`` — Apps, holding insights, reporting, and notes.
    """

    APPS = "apps"
    PRODUCTS = "products"
    RESULTS = "results"
    PROCESS = "process"


class ColumnPosition(str, Enum):
    """Where to insert a new column relative to a reference column.

    Used by the ``add_*_column`` methods of :class:`Sheet` to place a new column
    ``LEFT_OF`` or ``RIGHT_OF`` an existing one.
    """

    LEFT_OF = "leftOf"
    RIGHT_OF = "rightOf"


class RowPosition(str, Enum):
    """Where to insert a new row relative to a reference row.

    Used by the row-adding methods of :class:`Sheet` (e.g. :meth:`Sheet.add_lookup_row`,
    :meth:`Sheet.add_app_row`) to place a new row ``ABOVE`` or ``BELOW`` an existing one.
    """

    ABOVE = "above"
    BELOW = "below"


class Cell(BaseResource):
    """A single cell in a Sheet grid, at the intersection of a Column and a Row.

    A Cell is a live grid element: it carries the session and knows its position
    (via ``column_id``, ``row_id``, and ``design_id``) as well as its value,
    calculation, and formatting. Cells are typically read from a Sheet's grid or
    from :attr:`Column.cells` / :attr:`Row.cells`, and written back with
    :meth:`Sheet.update_cells`.

    Attributes
    ----------
    column_id : str
        The ID of the Column this cell belongs to.
    row_id : str
        The ID of the Row this cell belongs to.
    value : str | dict | list
        The value of the cell. For an inventory cell this may be a dict rather
        than a plain string; see :attr:`raw_value` for the underlying value.
    min_value : str | None
        The minimum allowed value for inventory cells. Optional.
    max_value : str | None
        The maximum allowed value for inventory cells. Optional.
    row_label_name : str, optional
        The display name of the row this cell is in.
    type : CellType | str
        The type of the cell. Allowed values are the same as for :class:`CellType`.
    row_type : CellType, optional
        The type of the row containing this cell. Usually one of ``INV`` (inventory
        row), ``TOT`` (total row), ``TAS`` (task row), ``TAG``, ``PRC``, ``PDC``,
        ``BAT``, or ``BLK``.
    name : str | None
        The name of the cell. Optional. Default is None.
    calculation : str
        The formula backing the cell, if any (e.g. a total). Default is ``""``.
    design_id : str
        The ID of the Design (Sheet section) this cell is in.
    format : dict
        The cell formatting. Default is ``{}``. Keys are ``bgColor`` and
        ``fontColor``, with RGB string values such as ``"RGB(255, 255, 255)"``.
    raw_value : str
        The underlying value of the cell. For an inventory cell this is the
        inventory item's value. Read-only.
    color : str | None
        The background color of the cell. Read-only.
    """

    column_id: str = Field(alias="colId")
    row_id: str = Field(alias="rowId")
    row_label_name: str | None = Field(default=None, alias="lableName")
    value: str | dict | list = ""
    min_value: str | None = Field(default=None, alias="minValue")
    max_value: str | None = Field(default=None, alias="maxValue")
    type: CellType | str
    row_type: CellType | str | None = Field(default=None)
    name: str | None = Field(default=None)
    calculation: str = ""
    design_id: str
    format: dict = Field(default_factory=dict, alias="cellFormat")
    inventory_id: str | None = Field(default=None)

    @property
    def raw_value(self):
        if isinstance(self.value, str):
            return self.value
        else:
            return self.value["value"]

    @property
    def color(self):
        return self.format.get("bgColor", None)


class Component(BaseResource):
    """One ingredient and its amount within a formulation.

    A Component pairs an inventory item (:class:`~albert.resources.inventory.InventoryItem`)
    with the amount of it used in a formulation. Components are the input to
    :meth:`Sheet.add_formulation` and :meth:`Sheet.add_components_to_formulation`,
    which place each ingredient's amount into the appropriate Cell of a
    formulation Column. Provide either ``inventory_item`` or ``inventory_id``;
    when ``inventory_item`` is given, ``inventory_id`` is populated from it
    automatically.

    Attributes
    ----------
    inventory_item : InventoryItem | None
        The inventory item in the component. Optional when ``inventory_id`` is provided.
    inventory_id : InventoryId | None
        The inventory ID backing the component (format ``INV...``). Automatically
        populated from ``inventory_item`` when present; required when
        ``inventory_item`` is omitted.
    amount : float
        The amount of the inventory item in the formulation.
    min_value : float | None
        The minimum allowed amount for the component. Optional.
    max_value : float | None
        The maximum allowed amount for the component. Optional.
    cell : Cell
        The cell the component was placed into. Read-only; set on registration.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.sheets import Component
        component = Component(inventory_id="INV1", amount=42.0)
        ```
    """

    inventory_item: InventoryItem | None = Field(default=None)
    inventory_id: InventoryId | None = Field(default=None)
    amount: float
    min_value: float | None = Field(default=None)
    max_value: float | None = Field(default=None)
    _cell: Cell = None  # read only property set on registrstion

    @model_validator(mode="after")
    def _ensure_inventory_reference(self: Component) -> Component:
        item = self.inventory_item
        if item is None and self.inventory_id is None:
            raise ValueError("Component requires either 'inventory_item' or 'inventory_id'.")
        if item is not None:
            if getattr(item, "id", None) is None:
                raise ValueError("Provided inventory_item must include an 'id'.")
            object.__setattr__(self, "inventory_id", item.id)
        return self

    @property
    def cell(self):
        return self._cell

    @property
    def inventory_item_id(self) -> InventoryId:
        if self.inventory_id:
            return self.inventory_id
        if self.inventory_item and getattr(self.inventory_item, "id", None):
            return self.inventory_item.id
        raise ValueError("Component is missing an inventory identifier.")


class DesignState(BaseResource):
    """The display state of a Design section within a Sheet.

    Attributes
    ----------
    collapsed : bool | None
        Whether the Design section is collapsed in the Sheet view. Default is False.
    """

    collapsed: bool | None = False


class RowConfig(BaseAlbertModel):
    """Configuration for an APP or location-type row."""

    option: str | None = Field(default=None)
    value: str | None = Field(default=None)


class RowGroup(BaseAlbertModel):
    """A named group of rows within a Design."""

    row_id: str = Field(alias="rowId")
    name: str | None = Field(default=None)
    child_row_ids: list[str] = Field(default_factory=list)


class Design(BaseSessionResource):
    """One section of a Sheet, backing the grid for a single :class:`DesignType`.

    A Sheet is made up of stacked sections — Product Design, Process Design,
    Results, and Apps — and each section is a Design. Designs are largely an
    internal detail: most work is done through the parent :class:`Sheet`, which
    exposes its Designs as :attr:`Sheet.product_design`,
    :attr:`Sheet.result_design`, :attr:`Sheet.app_design`, and
    :attr:`Sheet.process_design`. A Design is a live grid element that carries the
    session and lazily loads its rows, columns, and grid on first access.

    Attributes
    ----------
    id : str
        The Albert ID of the design.
    design_type : DesignType
        The section of the Sheet this design backs. See :class:`DesignType`.
    state : DesignState | None
        The display state of the design. Optional. Default is None.
    grid : pd.DataFrame | None
        The grid of the design, as a DataFrame of Cells. Loaded on first access.
        Read-only.
    rows : list[Row]
        The rows of the design. Loaded on first access. Read-only.
    columns : list[Column]
        The columns of the design. Loaded on first access. Read-only.

    Methods
    -------
    group_rows(name, child_row_ids, ...) -> RowGroup
        Create a named row group within this design.
    get_groups(refresh=False) -> list[RowGroup]
        Get all row groups in this design.
    """

    state: DesignState | None = Field({})
    id: str = Field(alias="albertId")
    design_type: DesignType = Field(alias="designType")
    _grid: pd.DataFrame | None = PrivateAttr(default=None)
    _rows: list[Row] | None = PrivateAttr(default=None)
    _columns: list[Column] | None = PrivateAttr(default=None)
    _sheet: Union[Sheet, None] = PrivateAttr(default=None)  # noqa
    _leftmost_pinned_column: str | None = PrivateAttr(default=None)
    _groups_cache: list[RowGroup] | None = PrivateAttr(default=None)

    def _grid_to_cell_df(self, *, grid_response):
        items = grid_response.get("Items") or []
        if not items:
            return pd.DataFrame()

        records: list[dict[str, Cell]] = []
        index: list[str] = []
        for item in items:
            this_row_id = item["rowId"]
            this_index = item["rowUniqueId"]
            row_label = item.get("lableName") or item.get("name")
            row_type = item["type"]

            index.append(this_index)
            row_cells: dict[str, Cell] = {}

            for raw_cell in item["Values"]:
                c = raw_cell.copy()
                c["rowId"] = this_row_id
                c["design_id"] = self.id
                c["row_type"] = row_type
                c["lableName"] = row_label
                # Preserve inventory bounds when constructing the Cell
                min_value = raw_cell.get("minValue")
                max_value = raw_cell.get("maxValue")
                if min_value is not None:
                    c["minValue"] = min_value
                if max_value is not None:
                    c["maxValue"] = max_value
                raw_id = c.pop("id", None)
                inv = (raw_id if raw_id.startswith("INV") else f"INV{raw_id}") if raw_id else None
                c["inventory_id"] = inv

                cell = Cell(**c)

                col_id = c["colId"]
                label = inv or c.get("name")
                row_cells[f"{col_id}#{label}"] = cell

            records.append(row_cells)

        # Determine the leftmost pinned column (last pinned col before first unpinned col).
        # Guard i > 0: if the very first formula is unpinned there are no pinned columns
        # and Formulas[i - 1] would wrap to the last element (Python negative index).
        for i, fmt in enumerate(grid_response.get("Formulas", [])):
            state = fmt.get("state", {})
            if state.get("pinned") is None:
                if i > 0:
                    prev = grid_response["Formulas"][i - 1]
                    self._leftmost_pinned_column = prev["colId"]
                break

        return pd.DataFrame.from_records(records, index=index)

    @property
    def sheet(self):
        return self._sheet

    @property
    def grid(self):
        if self._grid is None:
            self._grid = self._get_grid()
        return self._grid

    def _get_columns(self, *, grid_response: dict) -> list[Column]:
        """
        Normalizes inventory IDs (always prefixed "INV") and—for the
        "Inventory ID" header—falls back to the row's top-level `id`
        when Values[].id is absent.

        Parameters
        ----------
        grid_response : dict
            The JSON-decoded payload from GET /worksheet/.../grid.

        Returns
        -------
        list[Column]
        """
        items = grid_response.get("Items") or []
        if not items:
            return []

        formulas = grid_response.get("Formulas") or []
        formula_by_col: dict[str, dict[str, Any]] = {
            f["colId"]: f for f in formulas if isinstance(f, dict) and f.get("colId")
        }

        first = items[0]
        # for the Inventory-ID column fallback
        row_item_id = first.get("id")

        cols: list[Column] = []
        for v in first["Values"]:
            col_id = v.get("colId")
            if not col_id:
                continue

            raw_id = v.get("id")
            if raw_id is None and v.get("name") == "Inventory ID":
                raw_id = row_item_id

            if raw_id:
                inv_id = raw_id if str(raw_id).startswith("INV") else f"INV{raw_id}"
            else:
                inv_id = None

            formula = formula_by_col.get(col_id) or {}
            state = formula.get("state") or {}

            display_name = v.get("name") or formula.get("name") or inv_id

            locked = state.get("locked")
            if locked is not None:
                locked = bool(locked)

            pinned = state.get("pinned") or None
            hidden = formula.get("hidden")
            if hidden is not None:
                hidden = bool(hidden)
            column_width = state.get("columnWidth") or None
            cols.append(
                Column(
                    colId=v["colId"],
                    name=display_name,
                    type=v["type"],
                    session=self.session,
                    sheet=self.sheet,
                    inventory_id=inv_id,
                    hidden=hidden,
                    locked=locked,
                    pinned=pinned,
                    column_width=column_width,
                )
            )

        return cols

    def _get_rows(self, *, grid_response: dict) -> list[Row]:
        """
        Parse the /grid response into a list of Row models.

        Parameters
        ----------
        grid_response : dict
            The JSON-decoded payload from GET /worksheet/.../grid.

        Returns
        -------
        list[Row]
            One Row per item in `Items`
        """
        items = grid_response.get("Items") or []
        if not items:
            return []

        rows: list[Row] = []
        for v in items:
            raw_id = v.get("id")
            if raw_id and not str(raw_id).startswith("INV"):
                raw_id = f"INV{raw_id}"
            inv_id = raw_id

            row_label = v.get("lableName") or v.get("name")

            rows.append(
                Row(
                    rowId=v["rowId"],
                    type=v["type"],
                    session=self.session,
                    design=self,
                    sheet=self.sheet,
                    name=row_label,
                    manufacturer=v.get("manufacturer"),
                    inventory_id=inv_id,
                )
            )

        return rows

    def _get_grid(self):
        if self.design_type == DesignType.PROCESS:
            endpoint = f"/api/v3/designs/{self.id}/grid"
        else:
            endpoint = f"/api/v3/worksheet/{self.id}/{self.design_type.value}/grid"
        response = self.session.get(endpoint)

        resp_json = response.json()
        self._columns = self._get_columns(grid_response=resp_json)
        self._rows = self._get_rows(grid_response=resp_json)
        return self._grid_to_cell_df(grid_response=resp_json)

    @property
    def columns(self) -> list[Column]:
        if not self._columns:
            self._get_grid()
        return self._columns

    @property
    def rows(self) -> list[Row]:
        if not self._rows:
            self._get_grid()
        return self._rows

    def group_rows(
        self,
        *,
        name: str,
        child_row_ids: list[str],
        reference_id: str | None = None,
        position: str = "above",
    ) -> RowGroup:
        """Create a row group within this design.

        Parameters
        ----------
        name : str
            The name of the row group.
        child_row_ids : list[str]
            Row IDs to include in the group. Must contain at least one ID.
        reference_id : str, optional
            The reference row ID for insertion. Defaults to the first child row.
        position : str, optional
            Position relative to ``reference_id``. One of ``"above"`` or ``"below"``.
            Default is ``"above"``.

        Returns
        -------
        RowGroup
            The created row group.

        Examples
        --------
        !!! example
            ```python
            design = sheet.product_design
            group = design.group_rows(name="Solvents", child_row_ids=["ROW2", "ROW3"])
            ```
        """
        if not child_row_ids:
            raise AlbertException("child_row_ids must include at least one row ID")

        seen: set[str] = set()
        ids = [x for x in child_row_ids if not (x in seen or seen.add(x))]

        if reference_id and reference_id in ids:
            ids = [reference_id] + [x for x in ids if x != reference_id]
        else:
            reference_id = ids[0]

        payload = {
            "name": name,
            "referenceId": reference_id,
            "position": position,
            "ChildRows": [{"rowId": rid} for rid in ids],
        }
        response = self.session.put(f"/api/v3/worksheet/{self.id}/designs/groups", json=payload)
        data = response.json()
        group = RowGroup(
            rowId=data.get("rowId", reference_id),
            name=data.get("name", name),
        )
        child_rows = data.get("ChildRows") or []
        group.child_row_ids = [r["rowId"] for r in child_rows if r.get("rowId")]
        if not group.child_row_ids:
            group.child_row_ids = ids

        existing = {g.row_id: g for g in (self._groups_cache or [])}
        existing[group.row_id] = group
        self._groups_cache = list(existing.values())
        self._rows = None
        return group

    def get_groups(self, *, refresh: bool = False) -> list[RowGroup]:
        """Get all row groups in this design.

        Parameters
        ----------
        refresh : bool, optional
            When True, re-fetches the group list even if cached. Default is False.

        Returns
        -------
        list[RowGroup]
            The row groups in this design.

        Examples
        --------
        !!! example
            ```python
            groups = sheet.product_design.get_groups()
            for group in groups:
                print(group.name, group.child_row_ids)
            ```
        """
        if self._groups_cache is not None and not refresh:
            return self._groups_cache

        try:
            response = self.session.get(f"/api/v3/worksheet/design/{self.id}/rows/sequence")
        except AlbertHTTPError:
            self._groups_cache = []
            return []

        seq = response.json()
        if not isinstance(seq, list):
            self._groups_cache = []
            return []

        groups: list[RowGroup] = []
        for item in seq:
            rid = item.get("rowId") or item.get("id")
            child_dicts = (
                item.get("children") or item.get("childRows") or item.get("ChildRows") or []
            )
            if rid and child_dicts:
                child_ids = [
                    (c.get("rowId") or c.get("id"))
                    for c in child_dicts
                    if isinstance(c, dict) and (c.get("rowId") or c.get("id"))
                ]
                groups.append(RowGroup(rowId=rid, name=item.get("name"), child_row_ids=child_ids))

        self._groups_cache = groups
        return groups


class SheetFormulationRef(BaseAlbertModel):
    """A reference to a formulation in a sheet"""

    id: str = Field(description="The Albert ID of the inventory item that is the formulation")
    name: str | None = Field(default=None, description="The name of the formulation")
    hidden: bool = Field(description="Whether the formulation is hidden")


class Sheet(BaseSessionResource):  # noqa:F811
    """An interactive grid within a Worksheet where formulations are built.

    A Sheet is one grid inside a Worksheet (:class:`~albert.resources.worksheets.Worksheet`).
    It is organized into stacked sections, each a :class:`Design`: Product Design
    (where formulations are built), Process Design, Results (Property Tasks and
    their data), and Apps (insights and notes). Access those sections through
    :attr:`product_design`, :attr:`process_design`, :attr:`result_design`, and
    :attr:`app_design`.

    A Sheet Column can be a formulation (the most common case for the SDK), a
    lookup column that displays an inventory attribute, or an ingredient name.
    Rows typically represent ingredients (inventory items) and their amounts.
    Adding a formulation to a Sheet is what registers a Formula inventory item.

    The Sheet is a live grid element that carries the session; its cells, columns,
    and rows are themselves interactive. Retrieve a Sheet from a Worksheet's
    :attr:`~albert.resources.worksheets.Worksheet.sheets`, then edit it in place
    with the methods below.

    Attributes
    ----------
    id : str
        The Albert ID of the sheet.
    name : str
        The name of the sheet.
    formulations : list[SheetFormulationRef]
        References to the formulations present on the sheet.
    hidden : bool
        Whether the sheet is hidden.
    is_column_right : bool | None
        When True, copied columns are placed to the right of the source column;
        when False, to the left.
    col_size_mode : str | None
        Column width sizing mode. Allowed values are ``"minimum"`` and
        ``"fitToColumn"``. ``None`` resets to the default grid width.
    designs : list[Design]
        The Designs (sections) of the sheet.
    project_id : str
        The ID of the Project the sheet belongs to (format ``PRO...``).
    grid : pd.DataFrame | None
        The full sheet grid, as a DataFrame of Cells. Loaded on first access.
        Read-only.
    columns : list[Column]
        The Product Design columns of the sheet. Read-only.
    rows : list[Row]
        The rows of the sheet, across all Designs. Read-only.

    Methods
    -------
    rename(new_name) -> Sheet
        Rename the sheet.
    add_formulation(formulation_name, components, ...) -> Column
        Build a formulation column from a list of components (registers a Formula).
    add_components_to_formulation(components, ...) -> Column
        Add components to an existing formulation column.
    add_formulation_columns(formulation_names, ...) -> list[Column]
        Add one or more empty formulation columns.
    add_inventory_row(inventory_id, ...) -> Row
        Add an ingredient (inventory) row.
    add_blank_row(row_name, ...) -> Row
        Add a blank row.
    add_lookup_row(name, ...) -> Row
        Add a lookup row.
    add_app_row(app_id, name, ...) -> Row
        Add an application row.
    add_blank_column(name, ...) -> Column
        Add a blank column.
    add_lookup_column(name, ...) -> Column
        Add a lookup column.
    add_function_column(name, ...) -> Column
        Add a function column.
    add_property_column(name, attribute_id, ...) -> Column
        Add a property/result column.
    get_column(...) -> Column
        Retrieve a column by column ID, inventory ID, or name.
    update_cells(cells) -> tuple[list[Cell], list[Cell]]
        Write changed cells back to the sheet.
    pin_columns(col_ids, side) -> None
        Pin columns to the left or right edge.
    unpin_columns(col_ids) -> None
        Unpin columns.
    lock_column(...) -> Column
        Lock or unlock a column.
    hide_column(col_id) -> None
        Hide a column.
    show_column(col_id) -> None
        Show a hidden column.
    set_columns_width(col_ids, width) -> None
        Set the display width of columns.
    delete_column(column_id) -> None
        Delete a column.
    delete_row(row_id, design_id) -> None
        Delete a row.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        worksheet = client.worksheets.get_by_project_id(project_id="PRO1")
        sheet = worksheet.sheets[0]
        print(sheet.grid)
        ```
    """

    id: str = Field(alias="albertId")
    name: str
    formulations: list[SheetFormulationRef] = Field(default_factory=list, alias="Formulas")
    hidden: bool
    is_column_right: bool | None = Field(default=None, alias="isColumnRight")
    col_size_mode: str | None = Field(default=None, alias="colSizeMode")
    _app_design: Design = PrivateAttr(default=None)
    _product_design: Design = PrivateAttr(default=None)
    _result_design: Design = PrivateAttr(default=None)
    _process_design: Design = PrivateAttr(default=None)
    designs: list[Design] = Field(alias="Designs")
    project_id: str = Field(alias="projectId")
    _grid: pd.DataFrame = PrivateAttr(default=None)
    _leftmost_pinned_column: str | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def set_session(self):
        if self.session is not None:
            for d in self.designs:
                d._session = self.session
        return self

    @property
    def app_design(self):
        return self._app_design

    @property
    def product_design(self):
        return self._product_design

    @property
    def result_design(self):
        return self._result_design

    @property
    def process_design(self):
        return self._process_design

    @model_validator(mode="after")
    def set_sheet_fields(self: Sheet) -> Sheet:
        for _idx, d in enumerate(self.designs):  # Instead of creating a new list
            d._sheet = self  # Set the reference to the sheet
            if d.design_type == DesignType.APPS:
                self._app_design = d
            elif d.design_type == DesignType.PRODUCTS:
                self._product_design = d
            elif d.design_type == DesignType.RESULTS:
                self._result_design = d
            elif d.design_type == DesignType.PROCESS:
                self._process_design = d
        return self

    @property
    def grid(self):
        if self._grid is None:
            design_order = [
                self.product_design,
                self.result_design,
                self.app_design,
                self.process_design,
            ]
            frames = [design.grid for design in design_order if design is not None]
            self._grid = pd.concat(frames) if frames else pd.DataFrame()
        return self._grid

    @grid.setter
    def grid(self, value: pd.DataFrame | None):
        if value is None:
            # I am sure I could do this better.
            self._grid = value
            self._leftmost_pinned_column = None
            for design in self.designs:
                design._grid = None  # Assuming Design has a grid property
                design._rows = None
                design._columns = None
        else:
            raise NotImplementedError("grid is a read-only property")

    @property
    def leftmost_pinned_column(self):
        """The leftmost pinned column in the sheet"""
        if self._leftmost_pinned_column is None:
            self._leftmost_pinned_column = self.app_design._leftmost_pinned_column

        return self._leftmost_pinned_column

    @property
    def columns(self) -> list[Column]:
        """The columns of a given sheet"""
        return self.product_design.columns

    @property
    def rows(self) -> list[Row]:
        """The rows of a given sheet"""
        rows = []
        for d in self.designs:
            rows.extend(d.rows)
        return rows

    def _design_lookup(self) -> dict[DesignType, Design]:
        mapping = {
            DesignType.APPS: self.app_design,
            DesignType.PRODUCTS: self.product_design,
            DesignType.RESULTS: self.result_design,
            DesignType.PROCESS: self.process_design,
        }
        return {
            design_type: design for design_type, design in mapping.items() if design is not None
        }

    def _resolve_design(self, design_type: DesignType) -> Design:
        lookup = self._design_lookup()
        if design_type not in lookup:
            raise AlbertException(f"No design found for type '{design_type.value}'")
        return lookup[design_type]

    def _get_design_id(self, *, design: DesignType):
        return self._resolve_design(design).id

    def _get_design(self, *, design: DesignType):
        return self._resolve_design(design)

    def rename(self, *, new_name: str):
        """Rename this sheet.

        Parameters
        ----------
        new_name : str
            The new name for the sheet.

        Returns
        -------
        Sheet
            This sheet, with its name updated.

        Examples
        --------
        !!! example
            ```python
            sheet.rename(new_name="Final trial")
            ```
        """
        endpoint = f"/api/v3/worksheet/sheet/{self.id}"

        payload = [{"attribute": "name", "operation": "update", "newValue": new_name}]

        self.session.patch(endpoint, json=payload)

        self.name = new_name
        return self

    def _reformat_formulation_addition_payload(self, *, response_json: dict) -> dict:
        new_dicts = []
        for item in response_json:
            this_dict = {
                "colId": item["Formulas"][0]["colId"],
                "Formulas": [
                    {
                        "formulaId": item["Formulas"][0]["formulaId"],
                        "name": item["name"],
                    }
                ],
                "name": item["name"],
                "type": item["type"],
                "session": self.session,
                "sheet": self,
                "inventory_id": item.get("id", None),
            }
            new_dicts.append(this_dict)
        return new_dicts

    def _clear_formulation_from_column(self, *, column: Column):
        cleared_cells = []
        for cell in column.cells:
            if cell.type == CellType.INVENTORY and cell.row_type != CellType.TOTAL:
                cell_copy = cell.model_copy(update={"value": "", "calculation": ""})
                cleared_cells.append(cell_copy)
        self.update_cells(cells=cleared_cells)

    def add_formulation(
        self,
        *,
        formulation_name: str,
        components: list[Component],
        inventory_id: InventoryId | None = None,
        enforce_order: bool = False,
        clear: bool = True,
    ) -> Column:
        """Build a formulation on this sheet from a list of components.

        This is the primary way to create a formulation. Each component
        (:class:`Component`) contributes an ingredient and its amount, which are
        written into a formulation column. Adding rows for any new ingredients and
        maintaining the column's Total cell are handled automatically. Building a
        formulation this way is what registers a Formula inventory item
        (:class:`~albert.resources.inventory.InventoryItem`).

        If a column named ``formulation_name`` already exists and ``clear`` is True,
        that column is emptied and reused; otherwise a new formulation column is added.

        Parameters
        ----------
        formulation_name : str
            The name of the formulation, used as the column header.
        components : list[Component]
            The ingredients and their amounts to place in the formulation.
        inventory_id : InventoryId, optional
            The inventory ID of an existing formulation column to target
            (format ``INV...``). Used to disambiguate when reusing a column.
        enforce_order : bool, optional
            When True, ingredient rows are arranged to match the order of
            ``components``, adding rows as needed. Default is False.
        clear : bool, optional
            When True, an existing column with the same name is cleared and reused
            rather than adding a duplicate. Default is True.

        Returns
        -------
        Column
            The formulation column that was created or updated.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert
            from albert.resources.sheets import Component
            client = Albert()
            worksheet = client.worksheets.get_by_project_id(project_id="PRO1")
            sheet = worksheet.sheets[0]
            column = sheet.add_formulation(
                formulation_name="Formulation A",
                components=[
                    Component(inventory_id="INV1", amount=80.0),
                    Component(inventory_id="INV2", amount=20.0),
                ],
            )
            ```
        """
        all_cells: list[Cell] = []
        existing_formulation_names = [x.name for x in self.columns]
        if clear and formulation_name in existing_formulation_names:
            # get the existing column and clear it out to put the new formulation in
            col = self.get_column(column_name=formulation_name, inventory_id=inventory_id)
            self._clear_formulation_from_column(column=col)
        else:
            col = self.add_formulation_columns(formulation_names=[formulation_name])[0]
        column_id = col.column_id

        self.grid = None  # reset the grid for saftey
        product_rows = list(self.product_design.rows)
        initial_row_ids = {row.row_id for row in product_rows}

        for component in components:
            component_inventory_id = component.inventory_item_id
            row_id = self._get_row_id_for_component(
                inventory_id=component_inventory_id,
                existing_cells=all_cells,
                enforce_order=enforce_order,
                product_rows=product_rows,
            )
            if row_id is None:
                raise AlbertException(f"No Component with id {component_inventory_id}")

            value = str(component.amount)
            min_value = str(component.min_value) if component.min_value is not None else None
            max_value = str(component.max_value) if component.max_value is not None else None
            this_cell = Cell(
                column_id=column_id,
                row_id=row_id,
                value=value,
                calculation="",
                type=CellType.INVENTORY,
                design_id=self.product_design.id,
                name=formulation_name,
                inventory_id=col.inventory_id,
                min_value=min_value,
                max_value=max_value,
            )
            all_cells.append(this_cell)

        new_row_ids = [row.row_id for row in product_rows if row.row_id not in initial_row_ids]

        total_row = next((r for r in product_rows if r.type == CellType.TOTAL), None)
        if total_row is not None:
            ingredient_row_ids = [
                row.row_id
                for row in product_rows
                if row.inventory_id is not None and row.row_id != total_row.row_id
            ]
            calculation = "=" + "+".join(f"{column_id}{row_id}" for row_id in ingredient_row_ids)
            total_cell = Cell(
                column_id=column_id,
                row_id=total_row.row_id,
                value=str(sum(component.amount for component in components)),
                calculation=calculation,
                type=CellType.TOTAL,
                design_id=self.product_design.id,
                name=formulation_name,
                inventory_id=col.inventory_id,
            )
            all_cells.append(total_cell)

            # When new ingredient rows were added to the sheet, every other existing
            # inventory column's Total cell must also include those rows in its
            # calculation formula.
            if new_row_ids:
                all_ingredient_row_ids = [
                    row.row_id
                    for row in product_rows
                    if row.inventory_id is not None and row.row_id != total_row.row_id
                ]
                for other_col in self.columns:
                    if other_col.column_id == column_id or other_col.type != CellType.INVENTORY:
                        continue
                    other_total_cell = next(
                        (
                            c
                            for c in other_col.cells
                            if isinstance(c, Cell) and c.row_id == total_row.row_id
                        ),
                        None,
                    )
                    if other_total_cell is None:
                        continue
                    new_calculation = "=" + "+".join(
                        f"{other_col.column_id}{rid}" for rid in all_ingredient_row_ids
                    )
                    all_cells.append(
                        other_total_cell.model_copy(update={"calculation": new_calculation})
                    )

        # Send ingredient cells first, then Total cells in a separate call.
        def _is_total_cell(c: Cell) -> bool:
            return c.row_type == CellType.TOTAL or c.type == CellType.TOTAL

        ingredient_cells = [c for c in all_cells if not _is_total_cell(c)]
        total_cells = [c for c in all_cells if _is_total_cell(c)]

        if ingredient_cells:
            self.update_cells(cells=ingredient_cells)

        if total_cells:
            # grid reset for safety
            self.grid = None
            self.update_cells(cells=total_cells)

        return self.get_column(column_id=column_id)

    @validate_call
    def add_components_to_formulation(
        self,
        *,
        formulation_name: str | None = None,
        column_id: str | None = None,
        inventory_id: InventoryId | None = None,
        components: list[Component],
        enforce_order: bool = False,
    ) -> Column:
        """Add components to an existing formulation column without clearing other cells.

        Exactly one of ``column_id``, ``inventory_id``, or ``formulation_name`` must be provided.

        Parameters
        ----------
        formulation_name : str, optional
            The name of the formulation column.
        column_id : str, optional
            The column ID of the formulation column.
        inventory_id : str, optional
            The inventory ID of the formulation column.
        components : list[Component]
            The components to append.
        enforce_order : bool, optional
            When True, rows are inserted in the order of ``components``. Default is False.

        Returns
        -------
        Column
            The updated formulation column.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.sheets import Component
            column = sheet.add_components_to_formulation(
                formulation_name="Formulation A",
                components=[Component(inventory_id="INV3", amount=5.0)],
            )
            ```
        """
        col = self.get_column(
            column_id=column_id, inventory_id=inventory_id, column_name=formulation_name
        )
        col_id = col.column_id
        self.grid = None

        product_rows = list(self.product_design.rows)
        all_cells: list[Cell] = []
        for component in components:
            inv_item = component.inventory_item
            item_id: InventoryId = inv_item.id if inv_item is not None else component.inventory_id
            row_id = self._get_row_id_for_component(
                inventory_id=item_id,
                existing_cells=all_cells,
                enforce_order=enforce_order,
                product_rows=product_rows,
            )
            if row_id is None:
                raise AlbertException(f"No row found for inventory ID {item_id}")

            all_cells.append(
                Cell(
                    column_id=col_id,
                    row_id=row_id,
                    value=str(component.amount),
                    calculation="",
                    type=CellType.INVENTORY,
                    design_id=self.product_design.id,
                    name=col.name or formulation_name or "",
                    inventory_id=col.inventory_id,
                    min_value=str(component.min_value)
                    if component.min_value is not None
                    else None,
                    max_value=str(component.max_value)
                    if component.max_value is not None
                    else None,
                )
            )

        self.update_cells(cells=all_cells)
        return self.get_column(column_id=col_id)

    def _get_row_id_for_component(
        self,
        *,
        inventory_id: InventoryId,
        existing_cells,
        enforce_order,
        product_rows: list[Row],
    ):
        sheet_inv_id = inventory_id
        matching_rows = [row for row in product_rows if row.inventory_id == sheet_inv_id]

        used_row_ids = [cell.row_id for cell in existing_cells]

        existing_inv_order: list[str] = []
        index_last_row = 0
        if enforce_order:
            existing_inv_order = [
                row.row_id for row in product_rows if row.inventory_id is not None
            ]
            for row_id in used_row_ids:
                if row_id in existing_inv_order:
                    this_row_index = existing_inv_order.index(row_id)
                    if this_row_index > index_last_row:
                        index_last_row = this_row_index

        for row in matching_rows:
            if row.row_id in used_row_ids:
                continue
            if not enforce_order:
                return row.row_id

            if row.row_id in existing_inv_order:
                if existing_inv_order.index(row.row_id) >= index_last_row:
                    return row.row_id
                continue

        if enforce_order:
            if existing_inv_order:
                reference_row_id = existing_inv_order[index_last_row]
                new_row = self.add_inventory_row(
                    inventory_id=inventory_id,
                    position={"reference_id": reference_row_id, "position": "below"},
                )

                insert_position = None
                for idx, row in enumerate(product_rows):
                    if row.row_id == reference_row_id:
                        insert_position = idx + 1
                        break
                if insert_position is None:
                    product_rows.append(new_row)
                else:
                    product_rows.insert(insert_position, new_row)
                return new_row.row_id

            new_row = self.add_inventory_row(inventory_id=inventory_id)
            product_rows.append(new_row)
            return new_row.row_id

        new_row = self.add_inventory_row(inventory_id=inventory_id)
        product_rows.append(new_row)
        return new_row.row_id

    def add_formulation_columns(
        self,
        *,
        formulation_names: list[str],
        starting_position: dict | None = None,
    ) -> list[Column]:
        """Add one or more empty formulation columns to this sheet.

        Creates the formulation columns without populating any ingredient amounts.
        To build a formulation and fill in its components in one step, use
        :meth:`add_formulation` instead.

        Parameters
        ----------
        formulation_names : list[str]
            The names of the formulation columns to add, used as column headers.
        starting_position : dict, optional
            Where to insert the new columns, as a dict with ``reference_id`` (a
            column ID) and ``position`` (``"leftOf"`` or ``"rightOf"``). Defaults
            to just right of the leftmost pinned column.

        Returns
        -------
        list[Column]
            The created formulation columns, in the order requested.

        Examples
        --------
        !!! example
            ```python
            columns = sheet.add_formulation_columns(
                formulation_names=["Formulation A", "Formulation B"]
            )
            ```
        """
        if starting_position is None:
            # Ensure pinned-column state is resolved before computing the reference position.
            if self.app_design is not None:
                _ = self.app_design.grid
            starting_position = {
                "reference_id": self.leftmost_pinned_column,
                "position": "rightOf",
            }
        sheet_id = self.id

        endpoint = f"/api/v3/worksheet/sheet/{sheet_id}/columns"

        # In case a user supplied a single formulation name instead of a list
        formulation_names = (
            formulation_names if isinstance(formulation_names, list) else [formulation_names]
        )

        payload = []
        for formulation_name in (
            formulation_names
        ):  # IS there a limit to the number I can add at once? Need to check this.
            # define payload for this item
            payload.append(
                {
                    "type": "INV",
                    "name": formulation_name,
                    "referenceId": starting_position["reference_id"],  # initially defined column
                    "position": starting_position["position"],
                }
            )
        response = self.session.post(endpoint, json=payload)

        self.grid = None
        new_dicts = self._reformat_formulation_addition_payload(response_json=response.json())
        return [Column(**x) for x in new_dicts]

    def add_blank_row(
        self,
        *,
        row_name: str,
        design: DesignType = DesignType.PRODUCTS,
        position: dict | None = None,
    ):
        """Add a blank (BLK) row to a Design section of this sheet.

        Parameters
        ----------
        row_name : str
            The display name of the new row.
        design : DesignType, optional
            Which Design section to add the row to. Default is ``DesignType.PRODUCTS``.
            Rows cannot be added to the Results design.
        position : dict, optional
            Where to insert the row, as a dict with ``reference_id`` (a row ID) and
            ``position`` (``"above"`` or ``"below"``). Defaults to above ``"ROW1"``.

        Returns
        -------
        Row
            The created row.

        Raises
        ------
        AlbertException
            If ``design`` is ``DesignType.RESULTS``.

        Examples
        --------
        !!! example
            ```python
            row = sheet.add_blank_row(row_name="Notes")
            ```
        """
        if design == DesignType.RESULTS:
            raise AlbertException("You cannot add rows to the results design")
        if position is None:
            position = {"reference_id": "ROW1", "position": "above"}
        endpoint = f"/api/v3/worksheet/design/{self._get_design_id(design=design)}/rows"

        payload = [
            {
                "type": "BLK",
                "name": row_name,
                "referenceId": position["reference_id"],
                "position": position["position"],
            }
        ]

        response = self.session.post(endpoint, json=payload)

        self.grid = None
        row_dict = response.json()[0]
        return Row(
            rowId=row_dict["rowId"],
            type=row_dict["type"],
            session=self.session,
            design=self._get_design(design=design),
            name=row_dict["name"],
            sheet=self,
        )

    def add_inventory_row(
        self,
        *,
        inventory_id: str,
        position: dict | None = None,
    ):
        """Add an ingredient (inventory) row to the Product Design.

        The row represents an inventory item that can then carry amounts in each
        formulation column. The ``INV`` prefix is added to ``inventory_id`` if absent.

        Parameters
        ----------
        inventory_id : str
            The inventory ID of the item to add as a row (format ``INV...``).
        position : dict, optional
            Where to insert the row, as a dict with ``reference_id`` (a row ID) and
            ``position`` (``"above"`` or ``"below"``). Defaults to above ``"ROW1"``.

        Returns
        -------
        Row
            The created inventory row.

        Examples
        --------
        !!! example
            ```python
            row = sheet.add_inventory_row(inventory_id="INV1")
            ```
        """
        if position is None:
            position = {"reference_id": "ROW1", "position": "above"}
        design_id = self.product_design.id
        endpoint = f"/api/v3/worksheet/design/{design_id}/rows"

        payload = {
            "type": "INV",
            "id": ("INV" + inventory_id if not inventory_id.startswith("INV") else inventory_id),
            "referenceId": position["reference_id"],
            "position": position["position"],
        }

        response = self.session.post(endpoint, json=payload)

        self.grid = None
        row_dict = response.json()
        return Row(
            rowId=row_dict["rowId"],
            inventory_id=inventory_id,
            type=row_dict["type"],
            session=self.session,
            design=self.product_design,
            sheet=self,
            name=row_dict["name"],
            id=row_dict["id"],
            manufacturer=row_dict["manufacturer"],
        )

    @validate_call
    def add_lookup_row(
        self,
        *,
        name: str,
        design: DesignType | str | None = DesignType.APPS,
        reference_id: str = "ROW1",
        position: RowPosition = RowPosition.ABOVE,
    ) -> Row:
        """Add a lookup (LKP) row to a design.

        Parameters
        ----------
        name : str
            The display name of the new row.
        design : DesignType or str, optional
            Which design to add the row to. Default is ``DesignType.APPS``.
        reference_id : str, optional
            The row ID to insert relative to. Defaults to ``"ROW1"``.
        position : RowPosition, optional
            Whether to insert ``ABOVE`` or ``BELOW`` the reference row.
            Default is ``ABOVE``.

        Returns
        -------
        Row
            The created row.

        Examples
        --------
        !!! example
            ```python
            row = sheet.add_lookup_row(name="Density")
            ```
        """
        if design == DesignType.RESULTS:
            raise AlbertException("Cannot add rows to the results design")
        design_obj = self._get_design(design=design)
        payload = [
            {
                "type": "LKP",
                "name": name,
                "referenceId": reference_id,
                "position": position.value,
            }
        ]
        response = self.session.post(
            f"/api/v3/worksheet/design/{design_obj.id}/rows", json=payload
        )
        self.grid = None
        data = response.json()[0] if isinstance(response.json(), list) else response.json()
        return Row(
            rowId=data["rowId"],
            type=data["type"],
            session=self.session,
            design=design_obj,
            sheet=self,
            name=data.get("lableName") or data.get("name") or name,
            inventory_id=data.get("id"),
            manufacturer=data.get("manufacturer"),
        )

    @validate_call
    def add_app_row(
        self,
        *,
        app_id: str,
        name: str,
        config: RowConfig | None = None,
        design: DesignType | str | None = DesignType.APPS,
        reference_id: str = "ROW1",
        position: RowPosition = RowPosition.ABOVE,
    ) -> Row:
        """Add an application (APP) row to a design.

        Parameters
        ----------
        app_id : str
            The ID of the application. The ``APP`` prefix is added automatically if absent.
        name : str
            The display name of the row.
        config : RowConfig, optional
            Row configuration (``option`` and ``value``). Used to scope the app
            to a location or region.
        design : DesignType or str, optional
            Which design to add the row to. Default is ``DesignType.APPS``.
        reference_id : str, optional
            The row ID to insert relative to. Defaults to ``"ROW1"``.
        position : RowPosition, optional
            Whether to insert ``ABOVE`` or ``BELOW`` the reference row.
            Default is ``ABOVE``.

        Returns
        -------
        Row
            The created row.

        Examples
        --------
        !!! example
            ```python
            row = sheet.add_app_row(app_id="APP1", name="Cost insight")
            ```
        """
        if design == DesignType.RESULTS:
            raise AlbertException("Cannot add rows to the results design")
        design_obj = self._get_design(design=design)
        app_id = app_id if app_id.startswith("APP") else f"APP{app_id}"

        payload: dict = {
            "type": "APP",
            "id": app_id,
            "name": name,
            "referenceId": reference_id,
            "position": position.value,
        }
        if config is not None:
            payload["config"] = config.model_dump(by_alias=True, mode="json", exclude_none=True)

        response = self.session.post(
            f"/api/v3/worksheet/design/{design_obj.id}/rows", json=[payload]
        )
        self.grid = None
        data = response.json()[0] if isinstance(response.json(), list) else response.json()
        return Row(
            rowId=data["rowId"],
            type=data["type"],
            session=self.session,
            design=design_obj,
            sheet=self,
            name=data.get("name") or name,
            inventory_id=data.get("id"),
            manufacturer=data.get("manufacturer"),
            config=data.get("config"),
        )

    def _filter_cells(self, *, cells: list[Cell], response_dict: dict):
        updated = []
        failed = []
        for c in cells:
            found = False
            for r in response_dict["UpdatedItems"]:
                if r["id"]["rowId"] == c.row_id and r["id"]["colId"] == c.column_id:
                    found = True
                    updated.append(c)
            if not found:
                failed.append(c)
        return (updated, failed)

    def _get_current_cell(self, *, cell: Cell) -> Cell:
        def _matches_column(column_label: str) -> bool:
            col_parts = column_label.split("#", 1)
            return col_parts[0] == cell.column_id

        def _matches_row(index_label: str) -> bool:
            row_parts = index_label.split("#", 2)
            if len(row_parts) < 2:
                return False
            return row_parts[0] == cell.design_id and row_parts[1] == cell.row_id

        filtered_columns = [col for col in self.grid.columns if _matches_column(col)]
        filtered_rows = [idx for idx in self.grid.index if _matches_row(idx)]

        for row in filtered_rows:
            for col in filtered_columns:
                # grid.loc may return numpy.NaN for missing cells
                value = self.grid.loc[row, col]
                if isinstance(value, Cell):
                    return value
        return None

    def _generate_attribute_change(
        self,
        *,
        new_value: CellAttributeValue,
        old_value: CellAttributeValue,
        api_attribute_name: str,
    ) -> PatchDatum | None:
        """Generates a change dictionary for a single attribute."""
        if new_value == old_value:
            return None

        if new_value is None or new_value in ("", {}):
            return PatchDatum(
                operation="delete",
                attribute=api_attribute_name,
                old_value=old_value,
            )
        if old_value is None or old_value in ("", {}):
            return PatchDatum(
                operation="add",
                attribute=api_attribute_name,
                new_value=new_value,
            )
        return PatchDatum(
            operation="update",
            attribute=api_attribute_name,
            old_value=old_value,
            new_value=new_value,
        )

    def _get_cell_changes(self, *, cell: Cell) -> CellChangePayload | None:
        current_cell = self._get_current_cell(cell=cell)
        if current_cell is None:
            # New cell not yet in grid; blank baseline generates "add" operations.
            current_cell = Cell(
                column_id=cell.column_id,
                row_id=cell.row_id,
                design_id=cell.design_id,
                type=cell.type,
            )

        data: list[PatchDatum] = []

        # Handle format change
        if cell.format != current_cell.format:
            if cell.format is None or cell.format == {}:
                data.append(
                    PatchDatum(
                        operation="delete",
                        attribute="cellFormat",
                        old_value=current_cell.format,
                    )
                )
            else:
                data.append(
                    PatchDatum(
                        operation="update",
                        attribute="cellFormat",
                        old_value=current_cell.format,
                        new_value=cell.format,
                    )
                )

        # Handle calculation change
        if cell.calculation != current_cell.calculation:
            change = self._generate_attribute_change(
                new_value=cell.calculation,
                old_value=current_cell.calculation,
                api_attribute_name="calculation",
            )
            if change:
                data.append(change)

        # Special handling for value, min_value, max_value
        value_attributes = [
            ("value", "cell"),
            ("min_value", "minValue"),
            ("max_value", "maxValue"),
        ]
        if cell.calculation is None or cell.calculation == "" or cell.row_type == CellType.TOTAL:
            for attr, api_attr in value_attributes:
                if not self._compare_cell_attributes(
                    cell=cell, existing_cell=current_cell, attribute=attr
                ):
                    change = self._generate_attribute_change(
                        new_value=getattr(cell, attr),
                        old_value=getattr(current_cell, attr),
                        api_attribute_name=api_attr,
                    )
                    if change:
                        data.append(change)

        if not data:
            return None

        return {"Id": {"rowId": cell.row_id, "colId": cell.column_id}, "data": data}

    def _compare_cell_attributes(self, *, cell: Cell, existing_cell: Cell, attribute: str):
        """Compares a given attribute of two cells, trying both string and float comparison."""
        new_value = getattr(cell, attribute)
        old_value = getattr(existing_cell, attribute)
        # Check if the strings are exactly equal
        if new_value == old_value:
            return True

        # Try to cast both strings to floats and compare
        try:
            float1 = float(new_value)
            float2 = float(old_value)
            if float1 == float2:
                return True
        except (ValueError, TypeError):
            # One or both strings could not be cast to a float
            pass

        # Return False if neither comparison returned True
        return False

    def update_cells(self, *, cells: list[Cell]):
        """Write changed cells back to the sheet.

        Compares each cell against the current grid and sends only the changed
        attributes (value, calculation, formatting, bounds). Higher-level methods
        such as :meth:`add_formulation` and :meth:`Column.recolor_cells` call this
        for you; use it directly when editing cells obtained from the grid.

        Parameters
        ----------
        cells : list[Cell]
            The cells to update. Typically copies of existing cells with modified
            values or formatting.

        Returns
        -------
        tuple[list[Cell], list[Cell]]
            A ``(updated, failed)`` pair: the cells that were successfully updated
            and the cells that failed to update.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.sheets import CellColor
            column = sheet.get_column(column_name="Formulation A")
            recolored = [c.model_copy(update={"format": {"bgColor": CellColor.YELLOW.value}})
                         for c in column.cells]
            updated, failed = sheet.update_cells(cells=recolored)
            ```
        """
        request_path_dict: dict[str, list[Cell]] = {}
        updated: list[Cell] = []
        failed: list[Cell] = []
        # sort by design ID
        for c in cells:
            if c.design_id not in request_path_dict:
                request_path_dict[c.design_id] = [c]
            else:
                request_path_dict[c.design_id].append(c)

        for design_id, cell_list in request_path_dict.items():
            payload_entries: list[tuple[CellChangePayload, Cell]] = []
            for cell in cell_list:
                change_dict = self._get_cell_changes(cell=cell)
                if change_dict is None:
                    continue

                is_calculation_cell = cell.calculation is not None and cell.calculation != ""
                max_items = 2 if is_calculation_cell else 1

                if len(change_dict["data"]) > max_items:
                    for item in change_dict["data"]:
                        single_change: CellChangePayload = {
                            "Id": change_dict["Id"],
                            "data": [item],
                        }
                        payload_entries.append((single_change, cell))
                else:
                    payload_entries.append((change_dict, cell))

            if not payload_entries:
                continue

            this_url = f"/api/v3/worksheet/{design_id}/values"
            pending_by_cell: dict[tuple[str, str], list[tuple[CellChangePayload, Cell]]] = {}
            for payload, cell in payload_entries:
                key = (payload["Id"]["rowId"], payload["Id"]["colId"])
                pending_by_cell.setdefault(key, []).append((payload, cell))

            ordered_keys = list(pending_by_cell.keys())

            def _unique_cells(cells: list[Cell]) -> list[Cell]:
                seen: set[tuple[str, str, str]] = set()
                result: list[Cell] = []
                for c in cells:
                    key = (c.design_id, c.row_id, c.column_id)
                    if key not in seen:
                        seen.add(key)
                        result.append(c)
                return result

            batch_index = 0
            while True:
                batch_payloads: list[CellChangePayload] = []
                batch_cells: list[Cell] = []
                for key in ordered_keys:
                    queue = pending_by_cell.get(key)
                    if queue:
                        payload, cell = queue.pop(0)
                        batch_payloads.append(payload)
                        batch_cells.append(cell)
                if not batch_payloads:
                    break

                payload_body = [
                    {
                        "Id": payload["Id"],
                        "data": [datum.model_dump(by_alias=True) for datum in payload["data"]],
                    }
                    for payload in batch_payloads
                ]
                response = self.session.patch(this_url, json=payload_body)
                target_cells = _unique_cells(batch_cells)

                if response.status_code == 204:
                    for c in target_cells:
                        if c not in updated:
                            updated.append(c)
                elif response.status_code == 206:
                    cell_results = self._filter_cells(
                        cells=target_cells, response_dict=response.json()
                    )
                    for c in cell_results[0]:
                        if c not in updated:
                            updated.append(c)
                    for c in cell_results[1]:
                        if c not in failed:
                            failed.append(c)
                else:
                    for c in target_cells:
                        if c not in failed:
                            failed.append(c)

                batch_index += 1

        # reset the in-memory grid after updates
        self.grid = None
        return (updated, failed)

    def _add_column(
        self,
        *,
        type: str,
        name: str,
        reference_id: str | None,
        position: ColumnPosition,
        extra: dict | None = None,
    ) -> Column:
        if reference_id is None:
            reference_id = (
                self.columns[-1].column_id if self.columns else self.leftmost_pinned_column
            )
        payload: dict = {
            "type": type,
            "name": name,
            "referenceId": reference_id,
            "position": position.value if isinstance(position, ColumnPosition) else position,
            **(extra or {}),
        }
        response = self.session.post(f"/api/v3/worksheet/sheet/{self.id}/columns", json=[payload])
        data = response.json()[0]
        data["sheet"] = self
        data["session"] = self.session
        self.grid = None
        return Column(**data)

    @validate_call
    def add_blank_column(
        self,
        *,
        name: str,
        reference_id: str | None = None,
        position: ColumnPosition = ColumnPosition.RIGHT_OF,
    ) -> Column:
        """Add a blank (BLK) column to this sheet.

        Parameters
        ----------
        name : str
            The display name of the new column.
        reference_id : str, optional
            The column ID to insert relative to. Defaults to the last column in the sheet.
        position : ColumnPosition, optional
            Whether to insert ``LEFT_OF`` or ``RIGHT_OF`` the reference column.
            Default is ``RIGHT_OF``.

        Returns
        -------
        Column
            The created column.

        Examples
        --------
        !!! example
            ```python
            column = sheet.add_blank_column(name="Notes")
            ```
        """
        return self._add_column(
            type="BLK", name=name, reference_id=reference_id, position=position
        )

    @validate_call
    def add_lookup_column(
        self,
        *,
        name: str,
        reference_id: str | None = None,
        position: ColumnPosition = ColumnPosition.RIGHT_OF,
    ) -> Column:
        """Add a lookup (LKP) column to this sheet.

        Parameters
        ----------
        name : str
            The display name of the new column.
        reference_id : str, optional
            The column ID to insert relative to. Defaults to the last column in the sheet.
        position : ColumnPosition, optional
            Whether to insert ``LEFT_OF`` or ``RIGHT_OF`` the reference column.
            Default is ``RIGHT_OF``.

        Returns
        -------
        Column
            The created column.

        Examples
        --------
        !!! example
            ```python
            column = sheet.add_lookup_column(name="CAS Number")
            ```
        """
        return self._add_column(
            type="LKP", name=name, reference_id=reference_id, position=position
        )

    @validate_call
    def add_function_column(
        self,
        *,
        name: str,
        reference_id: str | None = None,
        position: ColumnPosition = ColumnPosition.RIGHT_OF,
    ) -> Column:
        """Add a function (FNC) column to this sheet.

        Parameters
        ----------
        name : str
            The display name of the new column.
        reference_id : str, optional
            The column ID to insert relative to. Defaults to the last column in the sheet.
        position : ColumnPosition, optional
            Whether to insert ``LEFT_OF`` or ``RIGHT_OF`` the reference column.
            Default is ``RIGHT_OF``.

        Returns
        -------
        Column
            The created column.

        Examples
        --------
        !!! example
            ```python
            column = sheet.add_function_column(name="Cost per kg")
            ```
        """
        return self._add_column(
            type="FNC", name=name, reference_id=reference_id, position=position
        )

    @validate_call
    def add_property_column(
        self,
        *,
        name: str,
        attribute_id: str,
        data_column_id: DataColumnId | None = None,
        data_column_name: str | None = None,
        reference_id: str | None = None,
        position: ColumnPosition = ColumnPosition.RIGHT_OF,
    ) -> Column:
        """Add a property/result (RSL) column to this sheet.

        Exactly one of ``data_column_id`` or ``data_column_name`` must be provided;
        the other is fetched automatically.

        Parameters
        ----------
        name : str
            The display name of the new column.
        attribute_id : str
            The ID of the attribute (e.g. ``"ATR2020"``).
        data_column_id : DataColumnId, optional
            The data column ID (e.g. ``"DAC2900"``). Fetched from the API if omitted.
        data_column_name : str, optional
            The data column name. Fetched from the API if omitted.
        reference_id : str, optional
            The column ID to insert relative to. Defaults to the last column in the sheet.
        position : ColumnPosition, optional
            Whether to insert ``LEFT_OF`` or ``RIGHT_OF`` the reference column.
            Default is ``RIGHT_OF``.

        Returns
        -------
        Column
            The created column.

        Examples
        --------
        !!! example
            ```python
            column = sheet.add_property_column(
                name="Viscosity",
                attribute_id="ATR2020",
                data_column_name="Viscosity",
            )
            ```
        """
        if not data_column_id and not data_column_name:
            raise AlbertException("Provide at least one of data_column_id or data_column_name.")
        if not data_column_id or not data_column_name:
            from albert.collections.data_columns import DataColumnCollection

            dc_collection = DataColumnCollection(session=self.session)
            if data_column_id and not data_column_name:
                dc = dc_collection.get_by_id(id=data_column_id)
                data_column_name = dc.name
            else:
                dc = dc_collection.get_by_name(name=data_column_name)
                if dc is None:
                    raise AlbertException(f"No data column found with name '{data_column_name}'.")
                data_column_id = dc.id

        return self._add_column(
            type="RSL",
            name=name,
            reference_id=reference_id,
            position=position,
            extra={
                "id": attribute_id,
                "datacolumnId": data_column_id,
                "datacolumnName": data_column_name,
            },
        )

    @validate_call
    def pin_columns(
        self,
        *,
        col_ids: list[str],
        side: Literal["left", "right"],
    ) -> None:
        """Pin one or more columns to the left or right edge of the sheet.

        Parameters
        ----------
        col_ids : list[str]
            The column IDs to pin.
        side : "left" or "right"
            Which edge to pin to.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.pin_columns(col_ids=["COL1", "COL2"], side="left")
            ```
        """
        payload = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "pinned",
                    "colIds": col_ids,
                    "newValue": side,
                }
            ]
        }
        self.session.patch(f"/api/v3/worksheet/sheet/{self.id}/columns", json=payload)
        self.grid = None

    @validate_call
    def unpin_columns(self, *, col_ids: list[str]) -> None:
        """Unpin one or more columns.

        Parameters
        ----------
        col_ids : list[str]
            The column IDs to unpin.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.unpin_columns(col_ids=["COL1", "COL2"])
            ```
        """
        payload = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "pinned",
                    "colIds": col_ids,
                    "newValue": None,
                }
            ]
        }
        self.session.patch(f"/api/v3/worksheet/sheet/{self.id}/columns", json=payload)
        self.grid = None

    @validate_call
    def set_columns_width(self, *, col_ids: list[str], width: str) -> None:
        """Set the display width of one or more columns.

        Parameters
        ----------
        col_ids : list[str]
            Column IDs to update.
        width : str
            Width value, e.g. ``"142px"``.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.set_columns_width(col_ids=["COL1"], width="200px")
            ```
        """
        payload = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "columnWidth",
                    "colIds": col_ids,
                    "newValue": width,
                }
            ]
        }
        self.session.patch(f"/api/v3/worksheet/sheet/{self.id}/columns", json=payload)
        self.grid = None

    @validate_call
    def hide_column(self, *, col_id: str) -> None:
        """Hide a column.

        Parameters
        ----------
        col_id : str
            The column ID to hide.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.hide_column(col_id="COL5")
            ```
        """
        self.session.patch(
            f"/api/v3/worksheet/sheet/{self.id}/columns",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "hidden",
                        "colId": col_id,
                        "newValue": True,
                    }
                ]
            },
        )
        self.grid = None

    @validate_call
    def show_column(self, *, col_id: str) -> None:
        """Show a hidden column.

        Parameters
        ----------
        col_id : str
            The column ID to show.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.show_column(col_id="COL5")
            ```
        """
        self.session.patch(
            f"/api/v3/worksheet/sheet/{self.id}/columns",
            json={
                "data": [
                    {
                        "operation": "update",
                        "attribute": "hidden",
                        "colId": col_id,
                        "newValue": False,
                    }
                ]
            },
        )
        self.grid = None

    def delete_column(self, *, column_id: str) -> None:
        """Delete a column from this sheet.

        Parameters
        ----------
        column_id : str
            The ID of the column to delete.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.delete_column(column_id="COL5")
            ```
        """
        endpoint = f"/api/v3/worksheet/sheet/{self.id}/columns"
        payload = [{"colId": column_id}]
        self.session.delete(endpoint, json=payload)

        if self._grid is not None:  # if I have a grid loaded into memory, adjust it.
            self.grid = None

    def delete_row(self, *, row_id: str, design_id: str) -> None:
        """Delete a row from a Design section of this sheet.

        Parameters
        ----------
        row_id : str
            The ID of the row to delete.
        design_id : str
            The ID of the Design (section) the row belongs to.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            sheet.delete_row(row_id="ROW3", design_id=sheet.product_design.id)
            ```
        """
        endpoint = f"/api/v3/worksheet/design/{design_id}/rows"
        payload = [{"rowId": row_id}]
        self.session.delete(endpoint, json=payload)

        if self._grid is not None:  # if I have a grid loaded into memory, adjust it.
            self.grid = None

    def _find_column(self, *, column_id: str = "", column_name: str = ""):
        if column_id == None:
            column_id = ""
        if column_name == None:
            column_name = ""
        search_str = f"{column_id}#{column_name}"
        matches = [col for col in self.grid.columns if search_str in col]
        if len(matches) == 0:
            return None
        elif len(matches) > 1:
            raise AlbertException(
                f"Ambiguous match on column name {column_name}. Please try provided a column ID"
            )
        else:
            return self.grid[matches[0]]

    @validate_call
    def get_column(
        self,
        *,
        column_id: str | None = None,
        inventory_id: InventoryId | None = None,
        column_name: str | None = None,
    ) -> Column:
        """Retrieve a Column by its column ID, underlying inventory ID, or header name.

        Provide at least one of the three identifiers; the match must be unique.

        Parameters
        ----------
        column_id : str, optional
            The sheet column ID to match (e.g. ``"COL5"``).
        inventory_id : str, optional
            The underlying inventory ID to match (e.g. ``"INVP015-001"``).
        column_name : str, optional
            The human-readable header name of the column (e.g. ``"Formulation A"``).

        Returns
        -------
        Column
            The matching column.

        Raises
        ------
        AlbertException
            If no identifier is provided, no matching column is found, or multiple
            columns match.

        Examples
        --------
        !!! example
            ```python
            column = sheet.get_column(column_name="Formulation A")
            ```
        """

        if not (column_id or inventory_id or column_name):
            raise AlbertException(
                "Must provide at least one of column_id, inventory_id or column_name"
            )
        # Gather candidates matching your filters
        candidates: list[Column] = []
        for col in self.columns:
            if column_id and col.column_id != column_id:
                continue
            if inventory_id and col.inventory_id != inventory_id:
                continue
            if column_name and col.name != column_name:
                continue
            candidates.append(col)

        if not candidates:
            raise AlbertException(
                f"No column found matching id={column_id}, "
                f"inventory_id={inventory_id}, column_name={column_name}"
            )
        if len(candidates) > 1:
            raise AlbertException("Ambiguous column match; please be more specific.")

        return candidates[0]

    def lock_column(
        self,
        *,
        column_id: str | None = None,
        inventory_id: InventoryId | None = None,
        column_name: str | None = None,
        locked: bool = True,
    ) -> Column:
        """Lock or unlock a column in the sheet.

        The column can be specified by its sheet column ID (e.g. ``"COL5"``),
        by the underlying inventory identifier of a formulation/product, or by
        the displayed header name. By default the column will be locked; pass
        ``locked=False`` to unlock it.

        Parameters
        ----------
        column_id : str | None
            The sheet column ID to match.
        inventory_id : str | None
            The inventory identifier of the formulation or product to match.
        column_name : str | None
            The displayed header name of the column.
        locked : bool
            Whether to lock (``True``) or unlock (``False``) the column. Defaults to
            ``True``.

        Returns
        -------
        Column
            The column that was updated.

        Examples
        --------
        !!! example
            ```python
            sheet.lock_column(column_name="Formulation A")
            ```
        """

        column = self.get_column(
            column_id=column_id, inventory_id=inventory_id, column_name=column_name
        )

        payload = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "locked",
                    "colIds": [column.column_id],
                    "newValue": locked,
                }
            ]
        }

        self.session.patch(
            url=f"/api/v3/worksheet/sheet/{self.id}/columns",
            json=payload,
        )

        self.grid = None

        return self.get_column(column_id=column.column_id)


class Column(BaseSessionResource):  # noqa:F811
    """A column in a Sheet.

    A Column is a live grid element that carries the session. A column can be a
    formulation (the most common case for the SDK), a lookup column that displays
    an inventory attribute, an ingredient name, or another type given by
    :class:`CellType`. Its cells are read through :attr:`cells` and written back
    with :meth:`Sheet.update_cells`.

    Attributes
    ----------
    column_id : str
        The ID of the column.
    name : str | None
        The header name of the column. Optional. Default is None.
    type : CellType | str
        The type of the column. Allowed values are the same as for :class:`CellType`.
    sheet : Sheet
        The sheet the column belongs to.
    inventory_id : str | None
        For a formulation column, the underlying inventory ID (format ``INV...``).
        Optional. Default is None.
    locked : bool
        Whether the column is locked against edits. Default is False.
    hidden : bool | None
        Whether the column is hidden. Optional. Default is None.
    pinned : str | None
        The edge the column is pinned to (``"left"`` or ``"right"``), or None.
    column_width : str | None
        The display width of the column (e.g. ``"142px"``), or None.
    cells : list[Cell]
        The cells in the column. Read-only.
    df_name : str
        The column's label in the sheet grid DataFrame. Read-only.

    Methods
    -------
    rename(new_name) -> Column
        Rename the column.
    recolor_cells(color) -> tuple[list[Cell], list[Cell]]
        Apply a background color to every cell in the column.
    """

    column_id: str = Field(alias="colId")
    name: str | None = Field(default=None)
    type: CellType | str
    sheet: Sheet
    inventory_id: str | None = Field(default=None, exclude=True)
    _cells: list[Cell] | None = PrivateAttr(default=None)
    locked: bool = Field(default=False)
    hidden: bool | None = Field(default=None)
    pinned: str | None = Field(default=None)
    column_width: str | None = Field(default=None)

    @field_validator("locked", mode="before")
    @classmethod
    def _none_to_false(cls, v):
        return False if v is None else v

    @property
    def df_name(self) -> str:
        if self.inventory_id is not None:
            return f"{self.column_id}#{self.inventory_id}"
        return f"{self.column_id}#{self.name}"

    @property
    def cells(self) -> list[Cell]:
        return self.sheet.grid[self.df_name]

    def rename(self, new_name):
        """Rename this column.

        Parameters
        ----------
        new_name : str
            The new header name for the column.

        Returns
        -------
        Column
            This column, with its name updated.

        Examples
        --------
        !!! example
            ```python
            column = sheet.get_column(column_name="Formulation A")
            column.rename("Formulation A (rev 2)")
            ```
        """
        payload = {
            "data": [
                {
                    "operation": "update",
                    "attribute": "name",
                    "colId": self.column_id,
                    "oldValue": self.name,
                    "newValue": new_name,
                }
            ]
        }

        self.session.patch(
            url=f"/api/v3/worksheet/sheet/{self.sheet.id}/columns",
            json=payload,
        )

        if self.sheet._grid is not None:  # if I have a grid loaded into memory, adjust it.
            self.sheet.grid = None
            # self.sheet._grid.rename(axis=1, mapper={self.name:new_name})
        self.name = new_name
        return self

    def recolor_cells(self, color: CellColor):
        """Apply a background color to every cell in this column.

        Parameters
        ----------
        color : CellColor
            The background color to apply.

        Returns
        -------
        tuple[list[Cell], list[Cell]]
            A ``(updated, failed)`` pair, as returned by :meth:`Sheet.update_cells`.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.sheets import CellColor
            column = sheet.get_column(column_name="Formulation A")
            column.recolor_cells(CellColor.BLUE)
            ```
        """
        new_cells = []
        for c in self.cells:
            cell_copy = c.model_copy(update={"format": {"bgColor": color.value}})
            new_cells.append(cell_copy)
        return self.sheet.update_cells(cells=new_cells)


class Row(BaseSessionResource):  # noqa:F811
    """A row in a Sheet.

    A Row is a live grid element that carries the session. Rows typically
    represent ingredients (inventory items) and their amounts, but a row can also
    be a total, lookup, app, or blank row per its :attr:`type`. Each row belongs
    to a specific :class:`Design` section of the :attr:`sheet`. Its cells are read
    through :attr:`cells` and written back with :meth:`Sheet.update_cells`.

    Attributes
    ----------
    row_id : str
        The ID of the row.
    type : CellType | str
        The type of the row. Allowed values are the same as for :class:`CellType`.
    design : Design
        The Design (section) the row belongs to.
    sheet : Sheet
        The sheet the row belongs to.
    name : str | None
        The display name of the row. Optional. Default is None.
    inventory_id : str | None
        For an ingredient row, the inventory ID of the item (format ``INV...``).
        Optional. Default is None.
    manufacturer : str | None
        The manufacturer of the row's inventory item. Optional. Default is None.
    config : RowConfig | None
        Configuration for APP or location-scoped rows. Optional. Default is None.
    parent_row_id : str | None
        The row ID of the group header this row belongs to. None if not grouped.
    child_row_ids : list[str]
        Row IDs of rows grouped under this row. Non-empty only on group header rows.
    is_group_header : bool
        True when this row is the header of a row group. Read-only.
    row_unique_id : str
        The unique ID of the row, combining its Design ID and row ID. Read-only.
    cells : list[Cell]
        The cells in the row. Read-only.

    Methods
    -------
    recolor_cells(color) -> tuple[list[Cell], list[Cell]]
        Apply a background color to every cell in the row.
    """

    row_id: str = Field(alias="rowId")
    type: CellType | str
    design: Design
    sheet: Sheet
    name: str | None = Field(default=None)
    inventory_id: str | None = Field(default=None, alias="id")
    manufacturer: str | None = Field(default=None)
    config: RowConfig | None = Field(default=None)
    parent_row_id: str | None = Field(default=None)
    child_row_ids: list[str] = Field(default_factory=list)

    @field_validator("config", mode="before")
    @classmethod
    def _coerce_config(cls, v):
        if v is None or isinstance(v, RowConfig):
            return v
        if isinstance(v, dict):
            return RowConfig(**v)
        return None

    @property
    def row_unique_id(self):
        return f"{self.design.id}#{self.row_id}"

    @property
    def is_group_header(self) -> bool:
        """True when this row is the header of a collapsed row group."""
        return bool(self.child_row_ids)

    @property
    def cells(self) -> list[Cell]:
        return self.sheet.grid.loc[self.row_unique_id]

    def recolor_cells(self, color: CellColor):
        """Apply a background color to every cell in this row.

        Parameters
        ----------
        color : CellColor
            The background color to apply.

        Returns
        -------
        tuple[list[Cell], list[Cell]]
            A ``(updated, failed)`` pair, as returned by :meth:`Sheet.update_cells`.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.sheets import CellColor
            row = sheet.rows[0]
            row.recolor_cells(CellColor.RED)
            ```
        """
        new_cells = []
        for c in self.cells:
            cell_copy = c.model_copy(update={"format": {"bgColor": color.value}})
            cell_copy.format = {"bgColor": color.value}
            new_cells.append(cell_copy)
        return self.sheet.update_cells(cells=new_cells)


# Resolve forward references after all classes are defined
Design.model_rebuild()
Row.model_rebuild()
Column.model_rebuild()
Sheet.model_rebuild()
