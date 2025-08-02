# Copyright Alexis de Lattre <alexis.delattre@akretion.com>
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

import uno
import unohelper
from com.sun.star.beans import PropertyValue
from tempfile import NamedTemporaryFile
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from stdnum.vatin import is_valid
from stdnum.de.stnr import is_valid as tax_id_is_valid
from stdnum.eu.vat import is_valid as eu_is_valid
from PyPDF4 import PdfFileWriter, PdfFileReader
from PyPDF4.generic import (
    DictionaryObject,
    DecodedStreamObject,
    NameObject,
    createStringObject,
    ArrayObject,
    IndirectObject,
)
from PyPDF4.utils import b_
import hashlib
import os
import mimetypes
import gettext

import factur_x_data

_ = gettext.gettext

INVOICE_REFUND_LANG = {
    # English
    "invoice": "380",
    "refund": "381",
    # German
    "rechnung": "380",
    "gutschrift": "381",
    # Add other langs here
}


def msg_box(doc, message):
    oSM = uno.getComponentContext().getServiceManager()
    oToolkit = oSM.createInstance("com.sun.star.awt.Toolkit")
    box_type = "errorbox"
    box_title = _("Factur-X Error")
    box_msg = str(message)
    box_button = 1  # OK button
    oParentWin = doc.getCurrentController().getFrame().getContainerWindow()
    oMsgBox = oToolkit.createMessageBox(
        oParentWin, box_type, box_button, box_title, box_msg
    )
    oMsgBox.execute()
    return False


def generate_facturx_xml(data, position_data, category_data):
    ns = {
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "rsm": "urn:un:unece:uncefact:data:standard:" "CrossIndustryInvoice:100",
        "ram": "urn:un:unece:uncefact:data:standard:"
        "ReusableAggregateBusinessInformationEntity:100",
        "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
        "udt": "urn:un:unece:uncefact:data:" "standard:UnqualifiedDataType:100",
    }
    ET.register_namespace("xsi", ns["xsi"])
    ET.register_namespace("rsm", ns["rsm"])
    ET.register_namespace("ram", ns["ram"])
    ET.register_namespace("qdt", ns["qdt"])
    ET.register_namespace("udt", ns["udt"])
    root = ET.Element(ET.QName(ns["rsm"], "CrossIndustryInvoice"))
    doc_ctx = ET.SubElement(root, ET.QName(ns["rsm"], "ExchangedDocumentContext"))
    ctx_param = ET.SubElement(
        doc_ctx, ET.QName(ns["ram"], "GuidelineSpecifiedDocumentContextParameter")
    )
    ctx_param_id = ET.SubElement(ctx_param, ET.QName(ns["ram"], "ID"))
    ctx_param_id.text = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
    header_doc = ET.SubElement(root, ET.QName(ns["rsm"], "ExchangedDocument"))
    header_doc_id = ET.SubElement(header_doc, ET.QName(ns["ram"], "ID"))
    header_doc_id.text = data["invoice_number"]
    header_doc_typecode = ET.SubElement(header_doc, ET.QName(ns["ram"], "TypeCode"))
    header_doc_typecode.text = data["invoice_or_refund"]
    date_node = ET.SubElement(header_doc, ET.QName(ns["ram"], "IssueDateTime"))
    date_node_str = ET.SubElement(
        date_node, ET.QName(ns["udt"], "DateTimeString"), format="102"
    )
    # 102 = format YYYYMMDD
    date_node_str.text = data["invoice_date"].strftime("%Y%m%d")
    if data.get("invoice_note"):
        header_doc_note = ET.SubElement(header_doc, ET.QName(ns["ram"], "IncludedNote"))
        header_doc_note_str = ET.SubElement(
            header_doc_note, ET.QName(ns["ram"], "Content")
        )
        header_doc_note_str.text = data["invoice_note"]

    if data.get("issuer_email"):
        header_doc_note = ET.SubElement(header_doc, ET.QName(ns["ram"], "IncludedNote"))
        header_doc_note_str = ET.SubElement(
            header_doc_note, ET.QName(ns["ram"], "Content")
        )
        header_doc_note_str.text = "Email: " + data["issuer_email"]

    if data.get("issuer_phone1"):
        header_doc_note = ET.SubElement(header_doc, ET.QName(ns["ram"], "IncludedNote"))
        header_doc_note_str = ET.SubElement(
            header_doc_note, ET.QName(ns["ram"], "Content")
        )
        header_doc_note_str.text = "Phone: " + data["issuer_phone1"]

    if data.get("issuer_add_contact_1"):
        header_doc_note = ET.SubElement(header_doc, ET.QName(ns["ram"], "IncludedNote"))
        header_doc_note_str = ET.SubElement(
            header_doc_note, ET.QName(ns["ram"], "Content")
        )
        header_doc_note_str.text = data["issuer_add_contact_1"]

    if data.get("issuer_add_contact_2"):
        header_doc_note = ET.SubElement(header_doc, ET.QName(ns["ram"], "IncludedNote"))
        header_doc_note_str = ET.SubElement(
            header_doc_note, ET.QName(ns["ram"], "Content")
        )
        header_doc_note_str.text = data["issuer_add_contact_2"]

    if data.get("issuer_tax_id"):
        header_doc_note = ET.SubElement(header_doc, ET.QName(ns["ram"], "IncludedNote"))
        header_doc_note_str = ET.SubElement(
            header_doc_note, ET.QName(ns["ram"], "Content")
        )
        header_doc_note_str.text = "National tax Id: " + data["issuer_tax_id"]

    trade_transaction = ET.SubElement(
        root, ET.QName(ns["rsm"], "SupplyChainTradeTransaction")
    )
    ########### Position Data ###########
    counter = 1
    for pos in position_data:
        trade_line_item = ET.SubElement(
            trade_transaction, ET.QName(ns["ram"], "IncludedSupplyChainTradeLineItem")
        )
        line = ET.SubElement(
            trade_line_item, ET.QName(ns["ram"], "AssociatedDocumentLineDocument")
        )
        line_id = ET.SubElement(line, ET.QName(ns["ram"], "LineID"))
        line_id.text = str(counter)
        counter += 1
        if pos.has_note():
            line_note = ET.SubElement(line, ET.QName(ns["ram"], "IncludedNote"))
            line_note_content = ET.SubElement(line_note, ET.QName(ns["ram"], "Content"))
            line_note_content.text = pos.note

        product = ET.SubElement(
            trade_line_item, ET.QName(ns["ram"], "SpecifiedTradeProduct")
        )
        product_name = ET.SubElement(product, ET.QName(ns["ram"], "Name"))
        product_name.text = pos.name

        line_trade = ET.SubElement(
            trade_line_item, ET.QName(ns["ram"], "SpecifiedLineTradeAgreement")
        )
        net_price = ET.SubElement(
            line_trade, ET.QName(ns["ram"], "NetPriceProductTradePrice")
        )
        net_price_amount = ET.SubElement(net_price, ET.QName(ns["ram"], "ChargeAmount"))
        net_price_amount.text = "%.4f" % pos.netto_price

        line_delivery = ET.SubElement(
            trade_line_item, ET.QName(ns["ram"], "SpecifiedLineTradeDelivery")
        )
        if pos.has_unit():
            amount_quantity = ET.SubElement(
                line_delivery, ET.QName(ns["ram"], "BilledQuantity"), unitCode=pos.unit
            )
        else:
            amount_quantity = ET.SubElement(
                line_delivery, ET.QName(ns["ram"], "BilledQuantity")
            )
        amount_quantity.text = "%.4f" % pos.amount
        line_settlement = ET.SubElement(
            trade_line_item, ET.QName(ns["ram"], "SpecifiedLineTradeSettlement")
        )
        line_tax = ET.SubElement(
            line_settlement, ET.QName(ns["ram"], "ApplicableTradeTax")
        )
        line_tax_type = ET.SubElement(line_tax, ET.QName(ns["ram"], "TypeCode"))
        line_tax_type.text = "VAT"
        line_tax_category = ET.SubElement(line_tax, ET.QName(ns["ram"], "CategoryCode"))
        line_tax_category.text = pos.tax_category
        line_tax_rate = ET.SubElement(
            line_tax, ET.QName(ns["ram"], "RateApplicablePercent")
        )
        line_tax_rate.text = "%.2f" % pos.tax_rate
        line_summation = ET.SubElement(
            line_settlement,
            ET.QName(ns["ram"], "SpecifiedTradeSettlementLineMonetarySummation"),
        )
        line_summation_amount = ET.SubElement(
            line_summation, ET.QName(ns["ram"], "LineTotalAmount")
        )
        line_summation_amount.text = "%.2f" % pos.netto_total

    trade_agreement = ET.SubElement(
        trade_transaction, ET.QName(ns["ram"], "ApplicableHeaderTradeAgreement")
    )

    ### Seller Trade Party ###
    seller = ET.SubElement(trade_agreement, ET.QName(ns["ram"], "SellerTradeParty"))
    seller_name = ET.SubElement(seller, ET.QName(ns["ram"], "Name"))
    seller_name.text = data["issuer_name"]

    seller_address = ET.SubElement(seller, ET.QName(ns["ram"], "PostalTradeAddress"))
    if data.get("issuer_address_postcode"):
        seller_address_postcode = ET.SubElement(
            seller_address, ET.QName(ns["ram"], "PostcodeCode")
        )
        seller_address_postcode.text = data["issuer_address_postcode"]
    if data.get("issuer_address_street"):
        seller_address_street = ET.SubElement(
            seller_address, ET.QName(ns["ram"], "LineOne")
        )
        seller_address_street.text = data["issuer_address_street"]
    if data.get("issuer_address_1"):
        seller_address_line1 = ET.SubElement(
            seller_address, ET.QName(ns["ram"], "LineTwo")
        )
        seller_address_line1.text = data["issuer_address_1"]
    if data.get("issuer_address_2"):
        seller_address_line2 = ET.SubElement(
            seller_address, ET.QName(ns["ram"], "LineThree")
        )
        seller_address_line2.text = data["issuer_address_2"]
    if data.get("issuer_address_city"):
        seller_address_city = ET.SubElement(
            seller_address, ET.QName(ns["ram"], "CityName")
        )
        seller_address_city.text = data["issuer_address_city"]
    seller_country_code = ET.SubElement(
        seller_address, ET.QName(ns["ram"], "CountryID")
    )
    seller_country_code.text = data["issuer_address_country_code"]
    if data.get("issuer_address_state"):
        seller_country_subdivision = ET.SubElement(
            seller_address, ET.QName(ns["ram"], "CountrySubDivisionName")
        )
        seller_country_subdivision.text = data["issuer_address_state"]

    seller_tax_reg = ET.SubElement(
        seller, ET.QName(ns["ram"], "SpecifiedTaxRegistration")
    )
    if data.get("issuer_vat_number"):
        seller_tax_reg_vat_id = ET.SubElement(
            seller_tax_reg, ET.QName(ns["ram"], "ID"), schemeID="VA"
        )
        seller_tax_reg_vat_id.text = data["issuer_vat_number"]
    elif data.get("issuer_tax_id"):
        seller_tax_reg_nat_id = ET.SubElement(
            seller_tax_reg, ET.QName(ns["ram"], "ID"), schemeID="FC"
        )
        seller_tax_reg_nat_id.text = data["issuer_tax_id"]
    ### Buyer Trade Party ###
    buyer = ET.SubElement(trade_agreement, ET.QName(ns["ram"], "BuyerTradeParty"))
    buyer_name = ET.SubElement(buyer, ET.QName(ns["ram"], "Name"))
    buyer_name.text = data["customer_name"]
    buyer_address = ET.SubElement(buyer, ET.QName(ns["ram"], "PostalTradeAddress"))
    if data.get("customer_address_postcode"):
        buyer_address_postcode = ET.SubElement(
            buyer_address, ET.QName(ns["ram"], "PostcodeCode")
        )
        buyer_address_postcode.text = data["customer_address_postcode"]
    if data.get("customer_address_street"):
        buyer_address_street = ET.SubElement(
            buyer_address, ET.QName(ns["ram"], "LineOne")
        )
        buyer_address_street.text = data["customer_address_street"]
    if data.get("customer_address_1"):
        buyer_address_line1 = ET.SubElement(
            buyer_address, ET.QName(ns["ram"], "LineTwo")
        )
        buyer_address_line1.text = data["customer_address_1"]
    if data.get("customer_address_2"):
        buyer_address_line2 = ET.SubElement(
            buyer_address, ET.QName(ns["ram"], "LineThree")
        )
        buyer_address_line2.text = data["customer_address_2"]
    if data.get("customer_address_city"):
        buyer_address_city = ET.SubElement(
            buyer_address, ET.QName(ns["ram"], "CityName")
        )
        buyer_address_city.text = data["customer_address_city"]
    buyer_country_code = ET.SubElement(buyer_address, ET.QName(ns["ram"], "CountryID"))
    buyer_country_code.text = data["customer_address_country_code"]
    if data.get("customer_address_state"):
        buyer_country_subdivision = ET.SubElement(
            buyer_address, ET.QName(ns["ram"], "CountrySubDivisionName")
        )
        buyer_country_subdivision.text = data["customer_address_state"]
    if data.get("customer_vat_number"):
        buyer_tax_reg = ET.SubElement(
            buyer, ET.QName(ns["ram"], "SpecifiedTaxRegistration")
        )
        buyer_tax_reg_id = ET.SubElement(
            buyer_tax_reg, ET.QName(ns["ram"], "ID"), schemeID="VA"
        )
        buyer_tax_reg_id.text = data["customer_vat_number"]
    ### customer order ref 2
    if data.get("customer_order_ref"):
        buyer_order_ref = ET.SubElement(
            trade_agreement, ET.QName(ns["ram"], "BuyerOrderReferencedDocument")
        )
        buyer_order_id = ET.SubElement(
            buyer_order_ref, ET.QName(ns["ram"], "IssuerAssignedID")
        )
        buyer_order_id.text = data["customer_order_ref"]
    ### Delivery block
    delivery = ET.SubElement(
        trade_transaction, ET.QName(ns["ram"], "ApplicableHeaderTradeDelivery")
    )
    ship_to_trade_party = ET.SubElement(
        delivery, ET.QName(ns["ram"], "ShipToTradeParty")
    )
    ship_to_name = ET.SubElement(ship_to_trade_party, ET.QName(ns["ram"], "Name"))
    ship_to_name.text = data["delivery_recipient"]
    ship_to_address = ET.SubElement(
        ship_to_trade_party, ET.QName(ns["ram"], "PostalTradeAddress")
    )
    if data.get("delivery_address_postcode"):
        ship_to_address_postcode = ET.SubElement(
            ship_to_address, ET.QName(ns["ram"], "PostcodeCode")
        )
        ship_to_address_postcode.text = data["delivery_address_postcode"]
    if data.get("delivery_address_street"):
        ship_to_address_street = ET.SubElement(
            ship_to_address, ET.QName(ns["ram"], "LineOne")
        )
        ship_to_address_street.text = data["delivery_address_street"]
    if data.get("delivery_address_1"):
        ship_to_address_line1 = ET.SubElement(
            ship_to_address, ET.QName(ns["ram"], "LineTwo")
        )
        ship_to_address_line1.text = data["delivery_address_1"]
    if data.get("delivery_address_2"):
        ship_to_address_line2 = ET.SubElement(
            ship_to_address, ET.QName(ns["ram"], "LineThree")
        )
        ship_to_address_line2.text = data["delivery_address_2"]
    if data.get("delivery_address_city"):
        ship_to_address_city = ET.SubElement(
            ship_to_address, ET.QName(ns["ram"], "CityName")
        )
        ship_to_address_city.text = data["delivery_address_city"]
    ship_to_country_code = ET.SubElement(
        ship_to_address, ET.QName(ns["ram"], "CountryID")
    )
    ship_to_country_code.text = data["delivery_address_country_code"]
    if data.get("delivery_address_state"):
        delivery_country_subdivision = ET.SubElement(
            ship_to_address, ET.QName(ns["ram"], "CountrySubDivisionName")
        )
        delivery_country_subdivision.text = data["delivery_address_state"]

    delivery_event = ET.SubElement(
        delivery, ET.QName(ns["ram"], "ActualDeliverySupplyChainEvent")
    )
    delivery_event_occurrence = ET.SubElement(
        delivery_event, ET.QName(ns["ram"], "OccurrenceDateTime")
    )
    delivery_date_str = ET.SubElement(
        delivery_event_occurrence, ET.QName(ns["udt"], "DateTimeString"), format="102"
    )
    # 102 = format YYYYMMDD
    delivery_date_str.text = data["delivery_date"].strftime("%Y%m%d")

    ### Header Trade Settlement
    trade_settlement = ET.SubElement(
        trade_transaction, ET.QName(ns["ram"], "ApplicableHeaderTradeSettlement")
    )
    invoice_currency = ET.SubElement(
        trade_settlement, ET.QName(ns["ram"], "InvoiceCurrencyCode")
    )
    invoice_currency.text = data["invoice_currency"]
    trade_tax = ET.SubElement(
        trade_settlement, ET.QName(ns["ram"], "ApplicableTradeTax")
    )
    ### tax category data
    for category in category_data:
        type = ET.SubElement(trade_tax, ET.QName(ns["ram"], "TypeCode"))
        type.text = "VAT"
        category_code = ET.SubElement(trade_tax, ET.QName(ns["ram"], "CategoryCode"))
        category_code.text = category.code
        category_rate = ET.SubElement(
            trade_tax, ET.QName(ns["ram"], "RateApplicablePercent")
        )
        category_rate.text = "%.2f" % category.rate

        if category.has_exempt_reason():
            exemption_reason = ET.SubElement(
                trade_tax, ET.QName(ns["ram"], "ExemptionReason")
            )
            exemption_reason.text = category.exempt_reason

        calculated_amount = ET.SubElement(
            trade_tax, ET.QName(ns["ram"], "CalculatedAmount")
        )
        calculated_amount.text = "%.2f" % category.sum_tax
        basis_amount = ET.SubElement(trade_tax, ET.QName(ns["ram"], "BasisAmount"))
        basis_amount.text = "%.2f" % category.taxed_amount

    if data.get("payment_instructions") or data.get("payment_due_date"):
        payment_terms = ET.SubElement(
            trade_settlement,
            ET.QName(ns["ram"], "SpecifiedTradePaymentTerms"),
        )
        if data.get("payment_instructions"):
            payment_terms_description = ET.SubElement(
                payment_terms, ET.QName(ns["ram"], "Description")
            )
            payment_terms_description.text = data["payment_instructions"]
        if data.get("payment_due_date"):
            payment_due_date = ET.SubElement(
                payment_terms, ET.QName(ns["udt"], "DateTimeString"), format="102"
            )
            # 102 = format YYYYMMDD
            payment_due_date.text = data["payment_due_date"].strftime("%Y%m%d")

    sums = ET.SubElement(
        trade_settlement,
        ET.QName(ns["ram"], "SpecifiedTradeSettlementHeaderMonetarySummation"),
    )
    line_total_amount = ET.SubElement(sums, ET.QName(ns["ram"], "LineTotalAmount"))
    line_total_amount.text = "%.2f" % data["total_without_tax"]

    if data.get("total_without_tax_inkl_charges"):
        tax_basis_total_amt = ET.SubElement(
            sums, ET.QName(ns["ram"], "TaxBasisTotalAmount")
        )
        tax_basis_total_amt.text = "%.2f" % data["total_without_tax_inkl_charges"]
    tax_total = ET.SubElement(
        sums, ET.QName(ns["ram"], "TaxTotalAmount"), currencyID=data["invoice_currency"]
    )
    tax_total.text = "%.2f" % data["total_tax"]
    total = ET.SubElement(sums, ET.QName(ns["ram"], "GrandTotalAmount"))
    total.text = "%.2f" % data["total_with_tax"]
    if data.get("deposits"):
        deposits = ET.SubElement(sums, ET.QName(ns["ram"], "TotalPrepaidAmount"))
        deposits.text = "%.2f" % data["deposits"]
    residual = ET.SubElement(sums, ET.QName(ns["ram"], "DuePayableAmount"))
    residual.text = "%.2f" % data["total_due"]
    xml_byte = ET.tostring(root)
    return xml_byte


def open_filepicker(title, path=None, mode=10, filter_tuple=None):
    """
    Possible modes: http://api.libreoffice.org/docs/idl/ref/namespacecom_1_1sun_1_1star_1_1ui_1_1dialogs_1_1TemplateDescription.html
    mode 0: simple open
    mode 10 : file save with option "automatic file name extension"
    """
    oCtx = uno.getComponentContext()
    oServiceManager = oCtx.getServiceManager()

    filepicker = oServiceManager.createInstanceWithArgumentsAndContext(
        "com.sun.star.ui.dialogs.OfficeFilePicker", (mode,), oCtx
    )
    if path:
        filepicker.setDisplayDirectory(path)
    if filter_tuple:
        filepicker.appendFilter(filter_tuple[0], filter_tuple[1])
    filepicker.Title = title
    if filepicker.execute():
        return filepicker.getFiles()[0]


def get_and_check_data(doc, data_sheet):
    fields = {
        "invoice_or_refund": {
            "type": "char",
            "required": True,
            "line": 3,
        },
        "invoice_number": {
            "type": "char",
            "required": True,
            "line": 4,
        },
        "customer_order_ref": {
            "type": "char",
            "required": False,
            "line": 5,
        },
        "invoice_date": {
            "type": "date",
            "required": True,
            "line": 6,
        },
        "delivery_date": {
            "type": "date",
            "required": True,
            "line": 7,
        },
        "invoice_note": {
            "type": "char",
            "required": False,
            "line": 8,
        },
        "issuer_name": {
            "type": "char",
            "required": True,
            "line": 10,
        },
        "issuer_address_street": {
            "type": "char",
            "required": False,
            "line": 11,
        },
        "issuer_address_1": {
            "type": "char",
            "required": False,
            "line": 12,
        },
        "issuer_address_2": {
            "type": "char",
            "required": False,
            "line": 13,
        },
        "issuer_address_postcode": {
            "type": "char",
            "required": False,
            "line": 14,
        },
        "issuer_address_city": {
            "type": "char",
            "required": False,
            "line": 15,
        },
        "issuer_address_country_code": {
            "type": "char",
            "required": True,
            "line": 16,
        },
        "issuer_address_state": {
            "type": "char",
            "required": False,
            "line": 17,
        },
        "issuer_vat_number": {
            "type": "char",
            "required": False,
            "line": 18,
        },
        "issuer_tax_id": {
            "type": "char",
            "required": False,
            "line": 19,
        },
        "issuer_phone1": {
            "type": "char",
            "required": False,
            "line": 20,
        },
        "issuer_add_contact_1": {
            "type": "char",
            "required": False,
            "line": 21,
        },
        "issuer_add_contact_2": {
            "type": "char",
            "required": False,
            "line": 22,
        },
        "issuer_email": {
            "type": "char",
            "required": False,
            "line": 23,
        },
        "issuer_note_1": {
            "type": "char",
            "required": False,
            "line": 25,
        },
        "issuer_note_2": {
            "type": "char",
            "required": False,
            "line": 26,
        },
        "customer_name": {
            "type": "char",
            "required": True,
            "line": 28,
        },
        "customer_address_street": {
            "type": "char",
            "required": False,
            "line": 29,
        },
        "customer_address_1": {
            "type": "char",
            "required": False,
            "line": 30,
        },
        "customer_address_2": {
            "type": "char",
            "required": False,
            "line": 31,
        },
        "customer_address_postcode": {
            "type": "char",
            "required": False,
            "line": 32,
        },
        "customer_address_city": {
            "type": "char",
            "required": False,
            "line": 33,
        },
        "customer_address_country_code": {
            "type": "char",
            "required": True,
            "line": 34,
        },
        "customer_address_state": {
            "type": "char",
            "required": False,
            "line": 35,
        },
        "customer_vat_number": {
            "type": "char",
            "required": False,
            "line": 36,
        },
        "delivery_recipient": {
            "type": "char",
            "required": True,
            "line": 38,
        },
        "delivery_address_street": {
            "type": "char",
            "required": False,
            "line": 39,
        },
        "delivery_address_1": {
            "type": "char",
            "required": False,
            "line": 40,
        },
        "delivery_address_2": {
            "type": "char",
            "required": False,
            "line": 41,
        },
        "delivery_address_postcode": {
            "type": "char",
            "required": False,
            "line": 42,
        },
        "delivery_address_city": {
            "type": "char",
            "required": False,
            "line": 43,
        },
        "delivery_address_country_code": {
            "type": "char",
            "required": True,
            "line": 44,
        },
        "delivery_address_state": {
            "type": "char",
            "required": False,
            "line": 45,
        },
        "payment_due_date": {
            "type": "date",
            "required": False,
            "line": 47,
        },
        "payment_instructions": {
            "type": "char",
            "required": False,
            "line": 48,
        },
        "invoice_currency": {
            "type": "char",
            "required": True,
            "line": 50,
        },
        "total_without_tax": {
            "type": "float",
            "required": True,
            "line": 52,
        },
        "total_without_tax_inkl_charges": {
            "type": "float",
            "required": False,
            "line": 53,
        },
        "total_tax": {
            "type": "float",
            "required": True,
            "line": 54,
        },
        "total_with_tax": {
            "type": "float",
            "required": True,
            "line": 55,
        },
        "deposits": {
            "type": "float",
            "required": False,
            "line": 56,
        },
        "total_due": {
            "type": "float",
            "required": True,
            "line": 57,
        },
        "attachment_count": {
            "type": "int",
            "required": False,
            "line": 59,
        },
    }

    data = {}
    # Read data
    for field, fdict in fields.items():
        valuecell = data_sheet.getCellByPosition(1, fdict["line"] - 1)
        labelcell = data_sheet.getCellByPosition(0, fdict["line"] - 1)
        fdict["label"] = labelcell.String
        if fdict["type"] == "float":
            value = valuecell.Value
        elif fdict["type"] == "int":
            value = valuecell.Value
            try:
                value = int(value)
            except Exception:
                value = 0
        elif fdict["type"] == "date":
            # when the cell is not recognised as a date, valuecell.Value = 0.0
            if valuecell.Value < 2:
                return msg_box(
                    doc,
                    _(
                        "In the second tab, cell B{line} ({label}) doesn't seem to be a date field. Check that the type of the cell has a date format. For that, right clic on the cell and select 'Format Cells': in the first tab, select 'Date' as 'Category' and check that the selected 'Format' matches the format currently used in the cell."
                    ).format(line=fdict["line"], label=fdict["label"]),
                )
            date_as_int = int(valuecell.Value)
            value = datetime.fromordinal(
                datetime(1900, 1, 1).toordinal() + date_as_int - 2
            )
        else:
            value = valuecell.String
        # check required fields are set
        if fdict["required"]:
            if fdict["type"] in ("date", "char") and not value:
                return msg_box(
                    doc,
                    _(
                        "In the second tab, cell B{line} ({label}) is a required field but it is currently empty or its type is wrong."
                    ).format(line=fdict["line"], label=fdict["label"]),
                )
            elif fdict["type"] == "float" and not value:
                value = 0.0
        if value or (fdict["type"] in ("float", "int") and fdict["required"]):
            data[field] = value

    # check if fields that are sometimes required are present
    if not data.get("issuer_vat_number") and not data.get("issuer_tax_id"):
        return msg_box(
            doc,
            _(
                "The invoice issuer must specify either a VAT number or a national tax id."
            ),
        )

    # Check data
    for field, fdict in fields.items():
        if field in data:
            value_display = data[field]
            if fdict["type"] == "date":
                value_display = data[field].strftime("%d %B %Y")
            msg_start = _(
                "In the second tab, the value of cell B{line} ({label}) is '{value}';"
            ).format(
                line=fdict["line"],
                label=fdict["label"],
                value=value_display,
            )
            msg_start += " "
            # check type
            if fdict["type"] == "float":
                if not isinstance(data[field], float):
                    return msg_box(doc, msg_start + _("it must be a float."))
                if data[field] < 0:
                    return msg_box(doc, msg_start + _("it must be positive."))
            elif fdict["type"] == "int":
                if not isinstance(data[field], int):
                    return msg_box(doc, msg_start + _("it must be an integer."))
                if data[field] < 0:
                    return msg_box(doc, msg_start + _("it must be positive."))
            elif fdict["type"] == "date":
                if not isinstance(data[field], datetime):
                    return msg_box(doc, msg_start + _("it must be a date."))
            elif fdict["type"] == "char":
                if not isinstance(data[field], str):
                    return msg_box(doc, msg_start + _("it must be a string."))
                data[field] = data[field].strip()
            # check specific fields
            if field.endswith("country_code"):  # required field
                if len(data[field]) != 2 or not data[field].isalpha():
                    return msg_box(
                        doc, msg_start + _("country codes must have 2 letters.")
                    )
                data[field] = data[field].upper()
            elif field.endswith("_vat_number"):
                if not is_valid(data[field]) and not eu_is_valid(data[field]):
                    msg_box(doc, msg_start + _("this VAT number is invalid."))
            elif field.endswith("_tax_id"):
                if not tax_id_is_valid(data[field]):
                    msg_box(doc, msg_start + _("this german tax number is invalid."))
            elif field == "invoice_currency":  # required field
                if len(data[field]) != 3 or not data[field].isalpha():
                    return msg_box(
                        doc, msg_start + _("currency codes must have 3 letters.")
                    )
                data[field] = data[field].upper()
            elif field == "invoice_date":
                date_text = data["invoice_date"].strftime("%Y%m%d")
                if date_text != datetime.today().strftime("%Y%m%d"):
                    return msg_box(
                        doc,
                        _(
                            "The invoice date must be today. If the entered date is correct please check your machines system settings."
                        ),
                    )
            elif field == "payment_due_date":
                date_text = data["payment_due_date"].strftime("%Y%m%d")
                if date_text < datetime.today().strftime("%Y%m%d"):
                    return msg_box(doc, _("The payment due date can't be in the past."))

    # Global checks
    diff = data["total_with_tax"] - data["total_without_tax"] - data["total_tax"]
    if abs(diff) > 0.00001:
        return msg_box(
            doc,
            _(
                "In the second tab, the value of cell B{line1} ({label1}: {val1}) must be equal to the value of cell B{line2} ({label2}: {val2}) plus cell B{line3} ({label3}: {val3})."
            ).format(
                line1=fields["total_with_tax"]["line"],
                label1=fields["total_with_tax"]["label"],
                val1=data["total_with_tax"],
                line2=fields["total_without_tax"]["line"],
                label2=fields["total_without_tax"]["label"],
                val2=data["total_without_tax"],
                line3=fields["total_tax"]["line"],
                label3=fields["total_tax"]["label"],
                val3=data["total_tax"],
            ),
        )
    deposits_value = 0.0
    if data.get("deposits"):
        deposits_value = data["deposits"]

    if abs(data["total_due"] - data["total_with_tax"] - deposits_value) > 0.00001:
        return msg_box(
            doc,
            _(
                "In the second tab, the value of cell B{line1} ({label1}: {val1}) must be equal to the value of cell B{line2} ({label2}: {val2}) plus cell B{line3} ({label3}: {val3})."
            ).format(
                line1=fields["total_due"]["line"],
                label1=fields["total_due"]["label"],
                val1=data["total_due"],
                line2=fields["total_with_tax"]["line"],
                label2=fields["total_with_tax"]["label"],
                val2=data["total_with_tax"],
                line3=fields["deposits"]["line"],
                label3=fields["deposits"]["label"],
                val3=deposits_value,
            ),
        )
    if not data.get("invoice_or_refund"):
        data["invoice_or_refund"] = "380"  # default value is invoice
    elif data["invoice_or_refund"].lower() in INVOICE_REFUND_LANG:
        data["invoice_or_refund"] = INVOICE_REFUND_LANG[
            data["invoice_or_refund"].lower()
        ]
    else:
        return msg_box(
            doc,
            _(
                "In the second tab, the value of cell B{line} ({label}) is '{value}'; it must be either 'invoice' or 'refund'."
            ).format(
                line=fields["invoice_or_refund"]["line"],
                label=fields["invoice_or_refund"]["label"],
                value=data["invoice_or_refund"],
            ),
        )
    return data


def get_position_data(doc, data_sheet, starting_line):
    last_position = 0
    position_data = []
    while True:
        # check if position index is valid and 1 bigger than previous
        cell_value = 0
        try:
            cell = data_sheet.getCellByPosition(0, starting_line - 1)
            cell_value = int(cell.Value)
        except ValueError:
            break
        if cell_value - 1 != last_position:
            break
        # line has position data, get it and check validity
        item = factur_x_data.ItemData()
        item.get_data_from_sheet(data_sheet, starting_line)
        if not item.is_valid():
            return msg_box(
                doc,
                _(
                    f"item {item.name} is not valid, check that all required fields are filled."
                ),
            )
            break
        position_data.append(item)
        # prepare for next loop
        last_position = cell_value
        starting_line += 1
    return position_data


def get_tax_category_data(doc, data_sheet, starting_line):
    last_position = 0
    category_data = []
    while True:
        # check if position index is valid and 1 bigger than previous
        cell_value = 0
        try:
            cell = data_sheet.getCellByPosition(0, starting_line - 1)
            cell_value = int(cell.getValue())
        except ValueError:
            break
        if cell_value - 1 != last_position:
            break
        # line has position data, get it and check validity
        category = factur_x_data.CategoryData()
        category.get_data_from_sheet(data_sheet, starting_line)
        if not category.is_valid():
            break
        category_data.append(category)
        # prepare for next loop
        last_position = cell_value
        starting_line += 1
    return category_data


def generate_facturx_invoice_v1(button_arg=None):
    doc = XSCRIPTCONTEXT.getDocument()
    macro_path = os.path.dirname(uno.fileUrlToSystemPath(__file__))
    localedir = os.path.join(macro_path, "i18n")
    gettext.bindtextdomain("facturx_macro", localedir=localedir)
    gettext.textdomain("facturx_macro")  # set 'facturx_macro' as global domain
    if len(doc.Sheets) < 2:
        return msg_box(doc, _("The spreadsheet must contain at least 2 tabs."))
    inv_sheet = doc.Sheets[0]
    data_sheet = doc.Sheets[1]
    # filter data
    data = get_and_check_data(doc, data_sheet)
    if not data:
        return

    # get category data
    starting_line_tax_categories = 62
    category_data = get_tax_category_data(doc, data_sheet, starting_line_tax_categories)
    category_check_result = factur_x_data.check_category_data(category_data)
    if category_check_result[0] == False:
        return msg_box(doc, category_check_result[1])

    # get position data from sheet
    position_starting_line = get_position_data_starting_line(
        doc, data_sheet, 62 + len(category_data) + 3, 0, 1, 2
    )
    if position_starting_line < 0:
        return msg_box(
            doc,
            _(
                "Could not find position data. Make sure it starts with position number 1 in column A and is located under the category data table."
            ),
        )
        return
    position_data = get_position_data(doc, data_sheet, position_starting_line)
    pos_check_result = factur_x_data.check_position_data(position_data)
    if pos_check_result[0] == False:
        return msg_box(doc, pos_check_result[1])

    # check that position and category data are consistent with general data
    calc_sum_tax = 0.00
    calc_sum_taxed_amount = 0.00
    for category in category_data:
        calc_sum_tax += category.sum_tax
        calc_sum_taxed_amount += category.taxed_amount
    if abs(calc_sum_tax - data["total_tax"]) > 0.0001:
        data_val = data["total_tax"]
        msg_box(
            doc,
            _(
                f"The sum of vat over all categories is not equal to the total tax. Total tax in invoice {data_val} vs calculated total tax {calc_sum_tax}"
            ),
        )
    if abs(calc_sum_taxed_amount - data["total_without_tax"]) > 0.0001:
        data_val = data["total_without_tax"]
        msg_box(
            doc,
            _(
                f"The taxed amount over all tax categories does not match the total without tax. Total tax in invoice {data_val} vs calculated total tax {calc_sum_taxed_amount}"
            ),
        )

    # Generate warning if category O is used together with differnet category
    category_set = set()
    for category in category_data:
        category_set.add(category.code)
    if "O" in category_set and len(category_set) > 1:
        msg_box(
            doc,
            _(
                "Invoices that use tax category O must not contain positions of any other tax category."
            ),
        )

    calc_net_sum = 0.00
    for pos in position_data:
        calc_net_sum += pos.netto_total
    if abs(calc_net_sum - data["total_without_tax"]) > 0.0001:
        msg_box(
            doc,
            _(
                "The net amount of all positions does not add up to the total without tax."
            ),
        )

    # prepare LO PDF export
    pdf_option1 = PropertyValue()
    pdf_option1.Name = "SelectPdfVersion"  # PDF/A
    pdf_option1.Value = 1
    pdf_option2 = PropertyValue()
    pdf_option2.Name = "Selection"  # Export 'Invoice' tab
    pdf_option2.Value = inv_sheet
    pdf_options = (pdf_option1, pdf_option2)

    pdf_export_arg1 = PropertyValue()
    pdf_export_arg1.Name = "FilterName"
    pdf_export_arg1.Value = "calc_pdf_Export"
    pdf_export_arg2 = PropertyValue()
    pdf_export_arg2.Name = "FilterData"
    pdf_export_arg2.Value = uno.Any("[]com.sun.star.beans.PropertyValue", pdf_options)
    pdf_export_args = (pdf_export_arg1, pdf_export_arg2)

    pdf_tmp_file = NamedTemporaryFile("w", prefix="libo-fx-", suffix=".pdf")
    pdf_tmp_file_url = uno.systemPathToFileUrl(pdf_tmp_file.name)
    doc.storeToURL(pdf_tmp_file_url, pdf_export_args)

    # generate XML
    xml_byte = generate_facturx_xml(data, position_data, category_data)
    if not xml_byte:
        return

    # Additionnal attachments
    additional_attachments = {}
    if data.get("attachment_count"):
        for a in range(data["attachment_count"]):
            attach_title = _("Select attachment No. {num}").format(num=a + 1)
            attachment_url = open_filepicker(attach_title, mode=0)
            if attachment_url:
                attach_filename = uno.fileUrlToSystemPath(attachment_url)
                additional_attachments[attach_filename] = ""

    # open "save-as" dialog box
    filter_tuple = ("PDF Files (.pdf)", "*.pdf")
    title = _("Save Factur-X PDF As")
    fx_pdf_filename_url = open_filepicker(title, filter_tuple=filter_tuple)
    if not fx_pdf_filename_url:  # when the user click on cancel in the dialog box
        return
    fx_pdf_filename = uno.fileUrlToSystemPath(fx_pdf_filename_url)

    pdf_metadata = {
        "author": data["issuer_name"],
        "keywords": ",".join(["Factur-X", _("Invoice")]),
        "title": _("{issuer}: Invoice {number}").format(
            issuer=data["issuer_name"], number=data["invoice_number"]
        ),
        "subject": _("Factur-X invoice {number} issued by {issuer}").format(
            number=data["invoice_number"], issuer=data["issuer_name"]
        ),
    }

    generate_facturx_from_file(
        pdf_tmp_file.name,
        xml_byte,
        facturx_level="basic",
        check_xsd=False,
        pdf_metadata=pdf_metadata,
        output_pdf_file=fx_pdf_filename,
        additional_attachments=additional_attachments,
    )
    pdf_tmp_file.close()

    # Open PDF viewer
    oCtx = uno.getComponentContext()
    oServiceManager = oCtx.getServiceManager()
    uno_openpdfviewer = oServiceManager.createInstanceWithContext(
        "com.sun.star.system.SystemShellExecute", oCtx
    )
    uno_openpdfviewer.execute(fx_pdf_filename_url, "", 0)
    return


def get_position_data_starting_line(
    doc, data_sheet, starting_line, column, value, num_lines
):
    for i in range(num_lines + 1):
        line_to_test = starting_line + i
        cell = data_sheet.getCellByPosition(column, line_to_test - 1)
        if not cell:
            continue
        try:
            cell_value = int(cell.Value)
        except ValueError:
            continue
        if cell_value == value:
            return line_to_test
    return -1


##################################################
# Include parts of my factur-x python lib here
# Why include the factur-x lib here instead of providing
# it under package/pythonpath as the PyPDF4 and stdnum libs ?
# Because the factur-x lib depends on lxml,
# and lxml is a Python binding on a C lib,
# which causes portability issues.
# So I decided to extract the parts of the factur-x lib that
# we need for this macro in this file (these parts don't depend
# on the lxml lib any more).


__version__ = "1.5libmacro"

FACTURX_FILENAME = "factur-x.xml"
FACTURX_LEVEL2xmp = {
    "minimum": "MINIMUM",
    "basicwl": "BASIC WL",
    "basic": "BASIC",
    "en16931": "EN 16931",
    "extended": "EXTENDED",
}


def _get_dict_entry(node, entry):
    if not isinstance(node, dict):
        raise ValueError("The node must be a dict")
    dict_entry = node.get(entry)
    if isinstance(dict_entry, dict):
        return dict_entry
    elif isinstance(dict_entry, IndirectObject):
        res_dict_entry = dict_entry.getObject()
        if isinstance(res_dict_entry, dict):
            return res_dict_entry
        else:
            return False
    else:
        return False


def _get_pdf_timestamp(date=None):
    if date is None:
        date = datetime.now()
    # example date format: "D:20141006161354+02'00'"
    pdf_date = date.strftime("D:%Y%m%d%H%M%S+00'00'")
    return pdf_date


def _get_metadata_timestamp():
    now_dt = datetime.now()
    # example format : 2014-07-25T14:01:22+02:00
    meta_date = now_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return meta_date


def _prepare_pdf_metadata_txt(pdf_metadata):
    pdf_date = _get_pdf_timestamp()
    info_dict = {
        "/Author": pdf_metadata.get("author", ""),
        "/CreationDate": pdf_date,
        "/Creator": "factur-x Python lib v%s by Alexis de Lattre" % __version__,
        "/Keywords": pdf_metadata.get("keywords", ""),
        "/ModDate": pdf_date,
        "/Subject": pdf_metadata.get("subject", ""),
        "/Title": pdf_metadata.get("title", ""),
    }
    return info_dict


def _prepare_pdf_metadata_xml(facturx_level, pdf_metadata):
    xml_str = """
<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" rdf:about="">
      <pdfaid:part>3</pdfaid:part>
      <pdfaid:conformance>B</pdfaid:conformance>
    </rdf:Description>
    <rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" rdf:about="">
      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">{title}</rdf:li>
        </rdf:Alt>
      </dc:title>
      <dc:creator>
        <rdf:Seq>
          <rdf:li>{author}</rdf:li>
        </rdf:Seq>
      </dc:creator>
      <dc:description>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">{subject}</rdf:li>
        </rdf:Alt>
      </dc:description>
    </rdf:Description>
    <rdf:Description xmlns:pdf="http://ns.adobe.com/pdf/1.3/" rdf:about="">
      <pdf:Producer>{producer}</pdf:Producer>
    </rdf:Description>
    <rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/" rdf:about="">
      <xmp:CreatorTool>{creator_tool}</xmp:CreatorTool>
      <xmp:CreateDate>{timestamp}</xmp:CreateDate>
      <xmp:ModifyDate>{timestamp}</xmp:ModifyDate>
    </rdf:Description>
    <rdf:Description xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/" xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#" xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#" rdf:about="">
      <pdfaExtension:schemas>
        <rdf:Bag>
          <rdf:li rdf:parseType="Resource">
            <pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>
            <pdfaSchema:namespaceURI>urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#</pdfaSchema:namespaceURI>
            <pdfaSchema:prefix>fx</pdfaSchema:prefix>
            <pdfaSchema:property>
              <rdf:Seq>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentFileName</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>name of the embedded XML invoice file</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentType</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>INVOICE</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>Version</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>The actual version of the Factur-X XML schema</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>ConformanceLevel</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>The conformance level of the embedded Factur-X data</pdfaProperty:description>
                </rdf:li>
              </rdf:Seq>
            </pdfaSchema:property>
          </rdf:li>
        </rdf:Bag>
      </pdfaExtension:schemas>
    </rdf:Description>
    <rdf:Description xmlns:fx="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#" rdf:about="">
      <fx:DocumentType>{facturx_documenttype}</fx:DocumentType>
      <fx:DocumentFileName>{facturx_filename}</fx:DocumentFileName>
      <fx:Version>{facturx_version}</fx:Version>
      <fx:ConformanceLevel>{facturx_level}</fx:ConformanceLevel>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
"""
    xml_str = xml_str.format(
        title=pdf_metadata.get("title", ""),
        author=pdf_metadata.get("author", ""),
        subject=pdf_metadata.get("subject", ""),
        producer="PyPDF4",
        creator_tool="factur-x python lib v%s by Alexis de Lattre" % __version__,
        timestamp=_get_metadata_timestamp(),
        facturx_documenttype="INVOICE",
        facturx_filename=FACTURX_FILENAME,
        facturx_version="1.0",
        facturx_level=FACTURX_LEVEL2xmp[facturx_level],
    )
    xml_byte = xml_str.encode("utf-8")
    return xml_byte


def _filespec_additional_attachments(
    pdf_filestream, name_arrayobj_cdict, file_dict, file_bin
):
    filename = file_dict["filename"]
    mod_date_pdf = _get_pdf_timestamp(file_dict["mod_date"])
    md5sum = hashlib.md5(file_bin).hexdigest()
    md5sum_obj = createStringObject(md5sum)
    params_dict = DictionaryObject(
        {
            NameObject("/CheckSum"): md5sum_obj,
            NameObject("/ModDate"): createStringObject(mod_date_pdf),
            NameObject("/Size"): NameObject(str(len(file_bin))),
        }
    )
    file_entry = DecodedStreamObject()
    file_entry.setData(file_bin)
    file_entry = file_entry.flateEncode()
    file_mimetype = mimetypes.guess_type(filename)[0]
    if not file_mimetype:
        file_mimetype = "application/octet-stream"
    file_mimetype_insert = "/" + file_mimetype.replace("/", "#2f")
    file_entry.update(
        {
            NameObject("/Type"): NameObject("/EmbeddedFile"),
            NameObject("/Params"): params_dict,
            NameObject("/Subtype"): NameObject(file_mimetype_insert),
        }
    )
    file_entry_obj = pdf_filestream._addObject(file_entry)
    ef_dict = DictionaryObject(
        {
            NameObject("/F"): file_entry_obj,
        }
    )
    fname_obj = createStringObject(filename)
    filespec_dict = DictionaryObject(
        {
            NameObject("/AFRelationship"): NameObject("/Unspecified"),
            NameObject("/Desc"): createStringObject(file_dict.get("desc", "")),
            NameObject("/Type"): NameObject("/Filespec"),
            NameObject("/F"): fname_obj,
            NameObject("/EF"): ef_dict,
            NameObject("/UF"): fname_obj,
        }
    )
    filespec_obj = pdf_filestream._addObject(filespec_dict)
    name_arrayobj_cdict[fname_obj] = filespec_obj


def _facturx_update_metadata_add_attachment(
    pdf_filestream,
    facturx_xml_str,
    pdf_metadata,
    facturx_level,
    output_intents=[],
    additional_attachments={},
):
    """This method is inspired from the code of the addAttachment()
    method of the PyPDF2 lib"""
    # The entry for the file
    # facturx_xml_str = facturx_xml_str.encode('utf-8')
    md5sum = hashlib.md5(facturx_xml_str).hexdigest()
    md5sum_obj = createStringObject(md5sum)
    params_dict = DictionaryObject(
        {
            NameObject("/CheckSum"): md5sum_obj,
            NameObject("/ModDate"): createStringObject(_get_pdf_timestamp()),
            NameObject("/Size"): NameObject(str(len(facturx_xml_str))),
        }
    )
    file_entry = DecodedStreamObject()
    file_entry.setData(facturx_xml_str)  # here we integrate the file itself
    file_entry = file_entry.flateEncode()
    file_entry.update(
        {
            NameObject("/Type"): NameObject("/EmbeddedFile"),
            NameObject("/Params"): params_dict,
            # 2F is '/' in hexadecimal
            NameObject("/Subtype"): NameObject("/text#2Fxml"),
        }
    )
    file_entry_obj = pdf_filestream._addObject(file_entry)
    # The Filespec entry
    ef_dict = DictionaryObject(
        {
            NameObject("/F"): file_entry_obj,
            NameObject("/UF"): file_entry_obj,
        }
    )

    fname_obj = createStringObject(FACTURX_FILENAME)
    filespec_dict = DictionaryObject(
        {
            NameObject("/AFRelationship"): NameObject("/Alternative"),
            NameObject("/Desc"): createStringObject("Factur-X Invoice"),
            NameObject("/Type"): NameObject("/Filespec"),
            NameObject("/F"): fname_obj,
            NameObject("/EF"): ef_dict,
            NameObject("/UF"): fname_obj,
        }
    )
    filespec_obj = pdf_filestream._addObject(filespec_dict)
    name_arrayobj_cdict = {fname_obj: filespec_obj}
    for attach_bin, attach_dict in additional_attachments.items():
        _filespec_additional_attachments(
            pdf_filestream, name_arrayobj_cdict, attach_dict, attach_bin
        )
    name_arrayobj_content_sort = list(
        sorted(name_arrayobj_cdict.items(), key=lambda x: x[0])
    )
    name_arrayobj_content_final = []
    af_list = []
    for fname_obj, filespec_obj in name_arrayobj_content_sort:
        name_arrayobj_content_final += [fname_obj, filespec_obj]
        af_list.append(filespec_obj)
    embedded_files_names_dict = DictionaryObject(
        {
            NameObject("/Names"): ArrayObject(name_arrayobj_content_final),
        }
    )
    # Then create the entry for the root, as it needs a
    # reference to the Filespec
    embedded_files_dict = DictionaryObject(
        {
            NameObject("/EmbeddedFiles"): embedded_files_names_dict,
        }
    )
    res_output_intents = []
    for output_intent_dict, dest_output_profile_dict in output_intents:
        dest_output_profile_obj = pdf_filestream._addObject(dest_output_profile_dict)
        # TODO detect if there are no other objects in output_intent_dest_obj
        # than /DestOutputProfile
        output_intent_dict.update(
            {
                NameObject("/DestOutputProfile"): dest_output_profile_obj,
            }
        )
        output_intent_obj = pdf_filestream._addObject(output_intent_dict)
        res_output_intents.append(output_intent_obj)
    # Update the root
    metadata_xml_str = _prepare_pdf_metadata_xml(facturx_level, pdf_metadata)
    metadata_file_entry = DecodedStreamObject()
    metadata_file_entry.setData(metadata_xml_str)
    metadata_file_entry = metadata_file_entry.flateEncode()
    metadata_file_entry.update(
        {
            NameObject("/Subtype"): NameObject("/XML"),
            NameObject("/Type"): NameObject("/Metadata"),
        }
    )
    metadata_obj = pdf_filestream._addObject(metadata_file_entry)
    af_value_obj = pdf_filestream._addObject(ArrayObject(af_list))
    pdf_filestream._root_object.update(
        {
            NameObject("/AF"): af_value_obj,
            NameObject("/Metadata"): metadata_obj,
            NameObject("/Names"): embedded_files_dict,
            # show attachments when opening PDF
            NameObject("/PageMode"): NameObject("/UseAttachments"),
        }
    )
    if res_output_intents:
        pdf_filestream._root_object.update(
            {
                NameObject("/OutputIntents"): ArrayObject(res_output_intents),
            }
        )
    metadata_txt_dict = _prepare_pdf_metadata_txt(pdf_metadata)
    pdf_filestream.addMetadata(metadata_txt_dict)


def _get_original_output_intents(original_pdf):
    output_intents = []
    try:
        pdf_root = original_pdf.trailer["/Root"]
        ori_output_intents = pdf_root["/OutputIntents"]
        for ori_output_intent in ori_output_intents:
            ori_output_intent_dict = ori_output_intent.getObject()
            dest_output_profile_dict = ori_output_intent_dict[
                "/DestOutputProfile"
            ].getObject()
            output_intents.append((ori_output_intent_dict, dest_output_profile_dict))
    except Exception:
        pass
    return output_intents


def generate_facturx_from_file(
    pdf_invoice,
    facturx_xml,
    facturx_level="autodetect",
    check_xsd=True,
    pdf_metadata=None,
    output_pdf_file=None,
    additional_attachments=None,
):
    """
    Generate a Factur-X invoice from a regular PDF invoice and a factur-X XML
    file. The method uses a file as input (regular PDF invoice) and re-writes
    the file (Factur-X PDF invoice).
    :param pdf_invoice: the regular PDF invoice as file path
    (type string) or as file object
    :type pdf_invoice: string or file
    :param facturx_xml: the Factur-X XML
    :type facturx_xml: bytes, string, file or etree object
    :param facturx_level: the level of the Factur-X XML file. Default value
    is 'autodetect'. The only advantage to specifiy a particular value instead
    of using the autodetection is for a very very small perf improvement.
    Possible values: minimum, basicwl, basic, en16931.
    :type facturx_level: string
    :param check_xsd: if enable, checks the Factur-X XML file against the XSD
    (XML Schema Definition). If this step has already been performed
    beforehand, you should disable this feature to avoid a double check
    and get a small performance improvement.
    :type check_xsd: boolean
    :param pdf_metadata: Specify the metadata of the generated Factur-X PDF.
    If pdf_metadata is None (default value), this lib will generate some
    metadata in English by extracting relevant info from the Factur-X XML.
    Here is an example for the pdf_metadata argument:
    pdf_metadata = {
        'author': 'Akretion',
        'keywords': 'Factur-X, Invoice',
        'title': 'Akretion: Invoice I1242',
        'subject':
          'Factur-X invoice I1242 dated 2017-08-17 issued by Akretion',
        }
    If you pass the pdf_metadata argument, you will not use the automatic
    generation based on the extraction of the Factur-X XML file, which will
    bring a very small perf improvement.
    :type pdf_metadata: dict
    :param output_pdf_file: File Path to the output Factur-X PDF file
    :type output_pdf_file: string or unicode
    :param additional_attachments: Specify the other files that you want to
    embed in the PDF file. It is a dict where keys are filepath and value
    is the description of the file (as unicode or string).
    :type additional_attachments: dict
    :return: Returns True. This method re-writes the input PDF invoice file,
    unless if the output_pdf_file is provided.
    :rtype: bool
    """
    assert isinstance(facturx_xml, bytes)
    xml_string = facturx_xml
    facturx_level = facturx_level.lower()
    additional_attachments_read = {}
    if additional_attachments:
        for attach_filepath, attach_desc in additional_attachments.items():
            filename = os.path.basename(attach_filepath)
            mod_timestamp = os.path.getmtime(attach_filepath)
            mod_dt = datetime.fromtimestamp(mod_timestamp)
            with open(attach_filepath, "rb") as fa:
                fa.seek(0)
                additional_attachments_read[fa.read()] = {
                    "filename": filename,
                    "desc": attach_desc,
                    "mod_date": mod_dt,
                }
                fa.close()
    original_pdf = PdfFileReader(pdf_invoice)
    # Extract /OutputIntents obj from original invoice
    output_intents = _get_original_output_intents(original_pdf)
    new_pdf_filestream = PdfFileWriter()
    new_pdf_filestream._header = b_("%PDF-1.6")
    new_pdf_filestream.appendPagesFromReader(original_pdf)

    original_pdf_id = original_pdf.trailer.get("/ID")
    if original_pdf_id:
        new_pdf_filestream._ID = original_pdf_id
        # else : generate some ?
    _facturx_update_metadata_add_attachment(
        new_pdf_filestream,
        xml_string,
        pdf_metadata,
        facturx_level,
        output_intents=output_intents,
        additional_attachments=additional_attachments_read,
    )
    if output_pdf_file:
        with open(output_pdf_file, "wb") as output_f:
            new_pdf_filestream.write(output_f)
            output_f.close()
    else:
        with open(pdf_invoice, "wb") as f:
            new_pdf_filestream.write(f)
            f.close()
    return True


# Only show the main method to the users
g_exportedScripts = (generate_facturx_invoice_v1,)

# Declare this Python file as a Macro in libreoffice
g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    None,
    "org.openoffice.script.DummyImplementationForPythonScripts",
    ("org.openoffice.script.DummyServiceForPythonScripts",),
)
