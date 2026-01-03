# Copyright 2025 Luise Preusse <pityrias@posteo.eu>
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

import os
import gettext

# Set up gettext to use the same domain and localedir as libreoffice_facturx_macro.py
macro_path = os.path.dirname(os.path.abspath(__file__))
localedir = os.path.join(macro_path, "i18n")
gettext.bindtextdomain("facturx_macro", localedir=localedir)
gettext.textdomain("facturx_macro")
_ = gettext.gettext

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
            and self.amount >= 0.00000
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


def check_position_data(position_data):
    if len(position_data) < 1:
        return (False, _("There must be at least one position listed"))
    cnt = 1
    for pos in position_data:
        if not pos.is_valid():
            return (False, _(f"Position {cnt} lacks required fields"))
        calc_price = round(pos.netto_price * pos.amount, 2)
        if abs(calc_price - pos.netto_total) > 0.001:
            return (
                False,
                _(
                    "Position {cnt}: netto total is not equal to netto price times the amount"
                ).format(cnt=cnt),
            )
        cnt += 1
    return (True, "")


def check_category_data(category_data):
    if len(category_data) < 1:
        return (False, _("There must be at least one tax category listed"))
    cnt = 1
    for category in category_data:
        if not category.is_valid():
            return (False, _(f"Tax category {cnt} lacks required fields"))
        calc_tax_total = round(category.rate / 100 * category.taxed_amount, 2)
        if abs(calc_tax_total - category.sum_tax) > 0.001:
            return (
                False,
                _(
                    "Tax category {cnt}: sum tax is not equal rate percent of taxed amount"
                ).format(cnt=cnt),
            )
        cnt += 1
    return (True, "")
