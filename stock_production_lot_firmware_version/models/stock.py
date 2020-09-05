# Copyright (C) 2017 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api,fields, models


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    firmware_version = fields.Char(string="Firmware Version")
    batch_no = fields.Char(string="Batch No ")
    manf = fields.Char(string="Manufacturer ")
    originc = fields.Char(string="Country of Origin ")
    prodDate = fields.Char(string="Production Date ")
    expDate = fields.Char(string="Expiry Date")
    qc_no = fields.Char(string="QC No ")
    name = fields.Char(
        'Lot/Serial Number',
        required=True, help="Unique Lot/Serial Number")

    @api.onchange('batch_no')
    def batch_no_changed(self):
        self.name=""
        if self.batch_no and self.qc_no:
            self.name=self.qc_no+"("+self.batch_no+")"
        elif self.batch_no :
            self.name=self.batch_no
        elif self.qc_no:
            self.name=self.qc_no


    @api.onchange('qc_no')
    def qc_no_changed(self):
        self.name=""
        if self.batch_no and self.qc_no:
            self.name=self.qc_no+"("+self.batch_no+")"
        elif self.batch_no :
            self.name=self.batch_no
        elif self.qc_no:
            self.name=self.qc_no