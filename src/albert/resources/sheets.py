from enum import Enum
from typing import ForwardRef, Union

import pandas as pd
from pydantic import Field, PrivateAttr, model_validator

from albert.exceptions import AlbertException
from albert.resources.base import BaseResource, BaseSessionResource
from albert.resources.inventory import InventoryItem
from albert.utils.types import BaseAlbertModel

# Define forward references
Row = ForwardRef("Row")
Column = ForwardRef("Column")
Sheet = ForwardRef("Sheet")


class CellColor(str, Enum):
    """The allowed colors for a cell"""

    WHITE = "RGB(255, 255, 255)"
    RED = "RGB(255, 161, 161)"
    GREEN = "RGB(130, 222, 198)"
    BLUE = "RGB(214, 233, 255)"
    YELLOW = "RGB(254, 240, 159)"
    ORANGE = "RGB(255, 227, 210)"
    PURPLE = "RGB(238, 215, 255)"


class CellType(str, Enum):
    """The type of information in the Cell"""

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


class DesignType(str, Enum):
    """The type of Design"""

    APPS = "apps"
    PRODUCTS = "products"
    RESULTS = "results"


class Cell(BaseResource):
    """A Cell in a Sheet

    Attributes
    ----------
    column_id : str
        The column ID of the cell.
    row_id : str
        The row ID of the cell.
    value : str | dict
        The value of the cell. If the cell is an inventory item, this will be a dict.
    type : CellType
        The type of the cell. Allowed values are `INV`, `APP`, `BLK`, `Formula`, `TAG`, `PRC`, `PDC`, `BAT`, `TOT`, `TAS`, `DEF`, `LKP`, `FOR`, and `EXTINV`.
    name : str | None
        The name of the cell. Optional. Default is None.
    calculation : str
        The calculation of the cell. Optional. Default is "".
    design_id : str
        The design ID of the design this cell is in.
    format : dict
        The format of the cell. Optional. Default is {}. The format is a dict with the keys `bgColor` and `fontColor`. The values are strings in the format `RGB(255, 255, 255)`.
    raw_value : str
        The raw value of the cell. If the cell is an inventory item, this will be the value of the inventory item. Read-only.
    color : str | None
        The color of the cell. Read only.
    """

    column_id: str = Field(alias="colId")
    row_id: str = Field(alias="rowId")
    value: str | dict = ""
    type: CellType
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
    """Represents an amount of an inventory item in a formulation

    Attributes
    ----------
    inventory_item : InventoryItem
        The inventory item in the component
    amount : float
        The amount of the inventory item in the component
    cell : Cell
        The cell that the component is in. Read-only.
    """

    inventory_item: InventoryItem
    amount: float
    _cell: Cell = None  # read only property set on registrstion

    @property
    def cell(self):
        return self._cell


class DesignState(BaseResource):
    """The state of a Design"""

    collapsed: bool | None = False


class Design(BaseSessionResource):
    """A Design in a Sheet. Designs are sheet subsections that are largly abstracted away from the user.

    Attributes
    ----------
    id : str
        The Albert ID of the design.
    design_type : DesignType
        The type of the design. Allowed values are `apps`, `products`, and `results`.
    state : DesignState | None
        The state of the design. Optional. Default is None.
    grid : pd.DataFrame | None
        The grid of the design. Optional. Default is None. Read-only.
    rows : list[Row] | None
        The rows of the design. Optional. Default is None. Read-only.
    columns : list[Column] | None
        The columns of the design. Optional. Default is None. Read-only.
    """

    state: DesignState | None = Field({})
    id: str = Field(alias="albertId")
    design_type: DesignType = Field(alias="designType")
    _grid: pd.DataFrame | None = PrivateAttr(default=None)
    _rows: list["Row"] | None = PrivateAttr(default=None)
    _columns: list["Column"] | None = PrivateAttr(default=None)
    _sheet: Union["Sheet", None] = PrivateAttr(default=None)  # noqa
    _leftmost_pinned_column: str | None = PrivateAttr(default=None)

    def _grid_to_cell_df(self, *, grid_response):
        all_rows = []
        all_index = []
        if not grid_response["Items"] or len(grid_response["Items"]) == 0:
            return pd.DataFrame()
        for item in grid_response["Items"]:
            row = {}
            this_row_id = item["rowId"]
            row_type = item["type"]
            this_index = item["rowUniqueId"]
            all_index.append(this_index)
            for c in item["Values"]:
                c["rowId"] = this_row_id
                c["design_id"] = self.id
                c["type"] = row_type
                c["inventory_id"] = c.get("id", None)
                this_cell = Cell(**c)
                col_id = c["colId"]
                inv_id = c.get("id", None)
                if inv_id is not None and not inv_id.startswith("INV"):
                    inv_id = "INV" + inv_id

                name = c.get("name", inv_id)
                if inv_id is None:
                    inv_id = name
                row[f"{col_id}#{inv_id}"] = this_cell
            all_rows.append(row)
        for i, state in enumerate(grid_response["Formulas"]):
            if state.get("state", None) is None or state["state"].get("pinned", None) is None:
                self._leftmost_pinned_column = grid_response["Formulas"][i - 1]["colId"]
                break
        return pd.DataFrame.from_records(all_rows, index=all_index)

    @property
    def sheet(self):
        return self._sheet

    @property
    def grid(self):
        if self._grid is None:
            self._grid = self._get_grid()
        return self._grid

    def _get_columns(self, *, grid_response) -> list["Column"]:
        columns = []
        # rsp_json = response.json()
        if not grid_response["Items"] or len(grid_response["Items"]) == 0:
            return []
        first_row = grid_response["Items"][0]
        for v in first_row["Values"]:
            inv_id = v.get("id", None)
            if inv_id is not None and not inv_id.startswith("INV"):
                inv_id = "INV" + inv_id
            if inv_id is None:
                inv_id = v.get("name", None)
            columns.append(
                Column(
                    colId=v["colId"],
                    name=inv_id,
                    type=v["type"],
                    session=self.session,
                    sheet=self.sheet,
                    inventory_id=inv_id,
                )
            )
        return columns

    def _get_rows(self, *, grid_response) -> list["Column"]:
        rows = []
        rows_dicts = grid_response["Items"]
        if not grid_response["Items"] or len(grid_response["Items"]) == 0:
            return []
        for v in rows_dicts:
            rows.append(
                Row(
                    name=v.get("name", None),
                    rowId=v["rowId"],
                    type=v["type"],
                    session=self.session,
                    design=self,
                    sheet=self.sheet,
                    manufacturer=v.get("manufacturer", None),
                    inventory_id=v.get("id", None),
                )
            )
        return rows

    def _get_grid(self):
        endpoint = f"/api/v3/worksheet/{self.id}/{self.design_type.value}/grid"
        response = self.session.get(endpoint)

        resp_json = response.json()
        self._columns = self._get_columns(grid_response=resp_json)
        self._rows = self._get_rows(grid_response=resp_json)
        return self._grid_to_cell_df(grid_response=resp_json)

    @property
    def columns(self) -> list["Column"]:
        if not self._columns:
            self._get_grid()
        return self._columns

    @property
    def rows(self) -> list["Row"]:
        if not self._rows:
            self._get_grid()
        return self._rows


class SheetFormulationRef(BaseAlbertModel):
    """A reference to a formulation in a sheet"""

    id: str = Field(description="The Albert ID of the inventory item that is the formulation")
    name: str = Field(description="The name of the formulation")
    hidden: bool = Field(description="Whether the formulation is hidden")


class Sheet(BaseSessionResource):  # noqa:F811
    """A Sheet in Albert

    Attributes
    ----------
    id : str
        The Albert ID of the sheet.
    name : str
        The name of the sheet.
    hidden : bool
        Whether the sheet is hidden.
    designs : list[Design]
        The designs of the sheet.
    project_id : str
        The Albert ID of the project the sheet is in.
    grid : pd.DataFrame | None
        The grid of the sheet. Optional. Default is None. Read-only.
    columns : list[Column]
        The columns of the sheet. Read-only.
    rows : list[Row]
        The rows of the sheet. Read-only.

    """

    id: str = Field(alias="albertId")
    name: str
    formulations: list[SheetFormulationRef] = Field(default_factory=list, alias="Formulas")
    hidden: bool
    _app_design: Design = PrivateAttr(default=None)
    _product_design: Design = PrivateAttr(default=None)
    _result_design: Design = PrivateAttr(default=None)
    designs: list[Design] = Field(alias="Designs")
    project_id: str
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

    @model_validator(mode="after")
    def set_sheet_fields(self: "Sheet") -> "Sheet":
        for _idx, d in enumerate(self.designs):  # Instead of creating a new list
            d._sheet = self  # Set the reference to the sheet
            if d.design_type == DesignType.APPS:
                self._app_design = d
            elif d.design_type == DesignType.PRODUCTS:
                self._product_design = d
            elif d.design_type == DesignType.RESULTS:
                self._result_design = d
        return self

    @property
    def grid(self):
        if self._grid is None:
            grids = [
                self.product_design,
                self.result_design,
                self.app_design,
            ]  # I don't just use the designs property, so I can ensure order.
            self._grid = pd.concat([x.grid for x in grids])
        return self._grid

    @grid.setter
    def grid(self, value: pd.DataFrame | None):
        if value is None:
            # I am sure I could do this better.
            self._grid = value
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
    def columns(self) -> list["Column"]:
        """The columns of a given sheet"""
        return self.app_design.columns

    @property
    def rows(self) -> list["Row"]:
        """The rows of a given sheet"""
        rows = []
        for d in self.designs:
            rows.extend(d.rows)
        return rows

    def _get_design_id(self, *, design: DesignType):
        if design == DesignType.APPS:
            return self.app_design.id
        elif design == DesignType.PRODUCTS:
            return self.product_design.id
        elif design == DesignType.RESULTS:
            return self.result_design.id

    def _get_design(self, *, design: DesignType):
        if design == DesignType.APPS:
            return self.app_design
        elif design == DesignType.PRODUCTS:
            return self.product_design
        elif design == DesignType.RESULTS:
            return self.result_design

    def rename(self, *, new_name: str):
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

    def _clear_formulation_from_column(self, *, column: "Column"):
        cleared_cells = []
        for cell in column.cells:
            if cell.type == CellType.INVENTORY:
                cell_copy = cell.model_copy(update={"value": "", "calculation": ""})
                cleared_cells.append(cell_copy)
        r = self.update_cells(cells=cleared_cells)
        return r

    def add_formulation(
        self, *, formulation_name: str, components: list[Component], enforce_order: bool = False
    ) -> "Column":
        existing_formulation_names = [x.name for x in self.columns]
        if formulation_name not in existing_formulation_names:
            col = self.add_formulation_columns(formulation_names=[formulation_name])[0]
        else:
            # get the existing column and clear it out to put the new formulation in
            col = self.get_column(column_name=formulation_name)
            self._clear_formulation_from_column(column=col)
        col_id = col.column_id

        all_cells = []
        self.grid = None  # reset the grid for saftey

        for component in components:
            row_id = self._get_row_id_for_component(
                inventory_item=component.inventory_item,
                existing_cells=all_cells,
                enforce_order=enforce_order,
            )
            if row_id is None:
                raise AlbertException(f"no component with id {component.inventory_item.id}")
            this_cell = Cell(
                column_id=col_id,
                row_id=row_id,
                value=str(component.amount),
                calculation="",
                type=CellType.INVENTORY,
                design_id=self.product_design.id,
                name=formulation_name,
                inventory_id=col.inventory_id,
            )
            all_cells.append(this_cell)

        self.update_cells(cells=all_cells)
        return self.get_column(column_id=col_id)

    def _get_row_id_for_component(self, *, inventory_item, existing_cells, enforce_order):
        self.grid = None

        # within a sheet, the "INV" prefix is dropped
        sheet_inv_id = inventory_item.id
        matching_rows = [x for x in self.product_design.rows if x.inventory_id == sheet_inv_id]

        used_row_ids = [x.row_id for x in existing_cells]
        if enforce_order:
            existing_inv_order = [
                x.row_id for x in self.product_design.rows if x.inventory_id is not None
            ]
            index_last_row = 0
            for row_id in used_row_ids:
                if row_id in existing_inv_order:
                    this_row_index = existing_inv_order.index(row_id)
                    if this_row_index > index_last_row:
                        index_last_row = this_row_index
        for r in matching_rows:
            if r.row_id not in used_row_ids:
                if enforce_order:
                    if existing_inv_order.index(r.row_id) >= index_last_row:
                        return r.row_id
                    else:
                        continue
                else:
                    return r.row_id
        # Otherwise I need to add a new row
        if enforce_order:
            return self.add_inventory_row(
                inventory_id=inventory_item.id,
                position={
                    "reference_id": existing_inv_order[index_last_row],
                    "position": "below",
                },
            ).row_id
        else:
            return self.add_inventory_row(inventory_id=inventory_item.id).row_id

    def add_formulation_columns(
        self,
        *,
        formulation_names: list[str],
        starting_position: dict | None = None,
    ) -> list["Column"]:
        if starting_position is None:
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
        design: DesignType | str | None = DesignType.PRODUCTS,
        position: dict | None = None,
    ):
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
        filtered_columns = [
            col for col in self.grid.columns if col.startswith(cell.column_id + "#")
        ]
        filtered_rows = [
            idx for idx in self.grid.index if idx.startswith(cell.design_id + "#" + cell.row_id)
        ]

        first_value = None
        for row in filtered_rows:
            for col in filtered_columns:
                first_value = self.grid.loc[row, col]
                return first_value
        return first_value

    def _get_cell_changes(self, *, cell: Cell) -> dict:
        current_cell = self._get_current_cell(cell=cell)
        change_dict = {
            "Id": {"rowId": cell.row_id, "colId": cell.column_id},
            "data": [],
        }
        if cell.calculation != current_cell.calculation:
            if cell.calculation is None or cell.calculation == "":
                change_dict["data"].append(
                    {
                        "operation": "delete",
                        "attribute": "calculation",
                        "oldValue": current_cell.calculation,
                    }
                )
            elif current_cell.calculation is None or current_cell.calculation == "":
                change_dict["data"].append(
                    {
                        "operation": "add",
                        "attribute": "calculation",
                        "newValue": cell.calculation,
                    }
                )
            else:
                change_dict["data"].append(
                    {
                        "operation": "update",
                        "attribute": "calculation",
                        "oldValue": current_cell.calculation,
                        "newValue": cell.calculation,
                    }
                )
        if cell.format != current_cell.format:
            if cell.format is None or cell.format == {}:
                change_dict["data"].append(
                    {
                        "operation": "delete",
                        "attribute": "cellFormat",
                        "oldValue": current_cell.format,
                    }
                )
            else:
                change_dict["data"].append(
                    {
                        "operation": "update",
                        "attribute": "cellFormat",
                        "oldValue": current_cell.format,
                        "newValue": cell.format,
                    }
                )
        if not self._compare_cell_values(cell=cell, existing_cell=current_cell) and (
            cell.calculation is None or cell.calculation == ""
        ):
            if cell.value is None or cell.value == "":
                change_dict["data"].append(
                    {
                        "operation": "delete",
                        "attribute": "cell",
                        "oldValue": current_cell.value,
                    }
                )
            elif current_cell.value is None or current_cell.value == "":
                change_dict["data"].append(
                    {
                        "operation": "add",
                        "attribute": "cell",
                        "newValue": cell.value,
                    }
                )
            else:
                change_dict["data"].append(
                    {
                        "operation": "update",
                        "attribute": "cell",
                        "oldValue": current_cell.value,
                        "newValue": cell.value,
                    }
                )
        if change_dict["data"] == []:
            return None
        return change_dict

    def _compare_cell_values(self, *, cell: Cell, existing_cell: Cell):
        # Check if the strings are exactly equal
        if cell.value == existing_cell.value:
            return True

        # Try to cast both strings to floats and compare
        try:
            float1 = float(cell.value)
            float2 = float(existing_cell.value)
            if float1 == float2:
                return True
        except ValueError:
            # One or both strings could not be cast to a float
            pass

        # Return False if neither comparison returned True
        return False

    def update_cells(self, *, cells: list[Cell]):
        request_path_dict = {}
        updated = []
        failed = []
        # sort by design ID
        for c in cells:
            if c.design_id not in request_path_dict:
                request_path_dict[c.design_id] = [c]
            else:
                request_path_dict[c.design_id].append(c)

        for design_id, cell_list in request_path_dict.items():
            payload = []
            for cell in cell_list:
                change_dict = self._get_cell_changes(cell=cell)
                if change_dict is not None:
                    payload.append(change_dict)

            if payload == []:
                continue

            this_url = f"/api/v3/worksheet/{design_id}/values"
            response = self.session.patch(
                this_url,
                json=payload,
            )

            if response.status_code == 204:
                # They all updated
                updated.extend(cell_list)
            elif response.status_code == 206:
                # Some updated and some did not.
                cell_results = self._filter_cells(cells=cell_list, response_dict=response.json())
                updated.extend(cell_results[0])
                failed.extend(cell_results[1])
        # reset the in-memory grid after updates
        self.grid = None
        return (updated, failed)

    def add_blank_column(self, *, name: str, position: dict = None):
        if position is None:
            position = {"reference_id": self.leftmost_pinned_column, "position": "rightOf"}
        endpoint = f"/api/v3/worksheet/sheet/{self.id}/columns"
        payload = [
            {
                "type": "BLK",
                "name": name,
                "referenceId": position["reference_id"],
                "position": position["position"],
            }
        ]

        response = self.session.post(endpoint, json=payload)

        data = response.json()
        data[0]["sheet"] = self
        data[0]["session"] = self.session
        self.grid = None  # reset the known grid. We could probably make this nicer later.
        return Column(**data[0])

    def delete_column(self, *, column_id: str) -> None:
        endpoint = f"/api/v3/worksheet/sheet/{self.id}/columns"
        payload = [{"colId": column_id}]
        self.session.delete(endpoint, json=payload)

        if self._grid is not None:  # if I have a grid loaded into memory, adjust it.
            self.grid = None

    def delete_row(self, *, row_id: str, design_id: str) -> None:
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

    def get_column(self, *, column_id: None | str = None, column_name: str | None = None):
        if column_id is None and column_name is None:
            raise AlbertException("Either a column name or id must be provided")
        else:
            matching_series = self._find_column(column_id=column_id, column_name=column_name)
            first_item = matching_series.iloc[0]
            inv_id = first_item.inventory_id
            if inv_id is not None and not inv_id.startswith("INV"):
                inv_id = "INV" + inv_id
            return Column(
                name=first_item.name,
                colId=first_item.column_id,
                type=first_item.type,
                sheet=self,
                session=self.session,
                inventory_id=first_item.inventory_id,
            )


class Column(BaseSessionResource):  # noqa:F811
    """A column in a Sheet

    Attributes
    ----------
    column_id : str
        The column ID of the column.
    name : str | None
        The name of the column. Optional. Default is None.
    type : CellType
        The type of the column. Allowed values are `INV`, `APP`, `BLK`, `Formula`, `TAG`, `PRC`, `PDC`, `BAT`, `TOT`, `TAS`, `DEF`, `LKP`, `FOR`, and `EXTINV`.
    sheet : Sheet
        The sheet the column is in.
    cells : list[Cell]
        The cells in the column. Read-only.
    df_name : str
        The name of the column in the DataFrame. Read-only
    """

    column_id: str = Field(alias="colId")
    name: str | None = Field(default=None)
    type: CellType
    sheet: Sheet
    inventory_id: str | None = Field(default=None, exclude=True)
    _cells: list[Cell] | None = PrivateAttr(default=None)

    @property
    def df_name(self):
        if self.inventory_id is not None:
            return f"{self.column_id}#{self.inventory_id}"
        return f"{self.column_id}#{self.name}"

    @property
    def cells(self) -> list[Cell]:
        return self.sheet.grid[self.df_name]

    def rename(self, new_name):
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
        new_cells = []
        for c in self.cells:
            cell_copy = c.model_copy(update={"format": {"bgColor": color.value}})
            new_cells.append(cell_copy)
        return self.sheet.update_cells(cells=new_cells)


class Row(BaseSessionResource):  # noqa:F811
    """A row in a Sheet

    Attributes
    ----------
    row_id : str
        The row ID of the row.
    type : CellType
        The type of the row. Allowed values are `INV`, `APP`, `BLK`, `Formula`, `TAG`, `PRC`, `PDC`, `BAT`, `TOT`, `TAS`, `DEF`, `LKP`, `FOR`, and `EXTINV`.
    design : Design
        The design the row is in.
    sheet : Sheet
        The sheet the row is in.
    name : str | None
        The name of the row. Optional. Default is None.
    inventory_id : str | None
        The inventory ID of the row. Optional. Default is None.
    manufacturer : str | None
        The manufacturer of the row. Optional. Default is None.
    row_unique_id : str
        The unique ID of the row. Read-only.
    cells : list[Cell]
        The cells in the row. Read-only.

    """

    row_id: str = Field(alias="rowId")
    type: CellType
    design: Design
    sheet: Sheet
    name: str | None = Field(default=None)
    inventory_id: str | None = Field(default=None, alias="id")
    manufacturer: str | None = Field(default=None)

    @property
    def row_unique_id(self):
        return f"{self.design.id}#{self.row_id}"

    @property
    def cells(self) -> list[Cell]:
        return self.sheet.grid.loc[self.row_unique_id]

    def recolor_cells(self, color: CellColor):
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
