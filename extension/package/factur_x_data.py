# Copyright 2025 Luise Preusse <preusseluise@mail.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import uno
import unohelper


class ItemData:

    def __init__(self):
        self.name = ""
        self.netto_price = float("nan")
        self.amount = float("nan")
        self.unit = ""
        self.tax_category = ""
        self.tax_rate = float("nan")
        self.netto_total = float("nan")
        self.note = ""

    def is_valid(self):
        valid = (
            len(self.name) != 0
            and self.netto_price != float("nan")
            and self.amount != float("nan")
            and len(self.tax_category) != 0
            and self.tax_rate != float("nan")
            and self.netto_total != float("nan")
        )
        return valid

    def has_unit(self):
        return len(self.unit) != 0

    def has_note(self):
        return len(self.note) != 0

    def get_data_from_sheet(self, data_sheet, line):
        cell = data_sheet.getCellByPosition(1, line - 1)
        if cell:
            self.name = cell.getString()

        cell = data_sheet.getCellByPosition(2, line - 1)
        if cell:
            self.netto_price = cell.getValue()

        cell = data_sheet.getCellByPosition(3, line - 1)
        if cell:
            self.amount = cell.getValue()

        cell = data_sheet.getCellByPosition(4, line - 1)
        if cell:
            self.unit = cell.getString()

        cell = data_sheet.getCellByPosition(5, line - 1)
        if cell:
            self.tax_category = cell.getString()

        cell = data_sheet.getCellByPosition(6, line - 1)
        if cell:
            self.tax_rate = cell.getValue()

        cell = data_sheet.getCellByPosition(7, line - 1)
        if cell:
            self.netto_total = cell.getValue()

        cell = data_sheet.getCellByPosition(8, line - 1)
        if cell:
            self.note = cell.getString()


class CategoryData:

    def __init__(self):
        self.code = ""
        self.rate = float("nan")
        self.sum_tax = float("nan")
        self.taxed_amount = float("nan")
        self.exempt_reason = ""

    def is_valid(self):
        zero_epsilon = -1e-04
        valid = (
            len(self.code) > 0
            and len(self.code) <= 2
            and self.rate > zero_epsilon
            and self.sum_tax > zero_epsilon
            and self.taxed_amount > zero_epsilon
        )
        return valid

    def has_exempt_reason(self):
        return len(self.exempt_reason) != 0

    def get_data_from_sheet(self, data_sheet, line):
        cell = data_sheet.getCellByPosition(1, line - 1)
        if cell:
            self.code = cell.getString()

        cell = data_sheet.getCellByPosition(2, line - 1)
        if cell:
            self.rate = cell.getValue()

        cell = data_sheet.getCellByPosition(3, line - 1)
        if cell:
            self.sum_tax = cell.getValue()

        cell = data_sheet.getCellByPosition(4, line - 1)
        if cell:
            self.taxed_amount = cell.getValue()

        cell = data_sheet.getCellByPosition(5, line - 1)
        if cell:
            self.exempt_reason = cell.getString()
