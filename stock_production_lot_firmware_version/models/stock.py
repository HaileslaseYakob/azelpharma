# Copyright (C) 2017 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api,fields, models



class Manufacturer(models.Model):
    _name = 'manufacturer'

    name=fields.Char("Name")

class Country(models.Model):
    _name = 'country'

    name=fields.Char("Name")

class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    firmware_version = fields.Char(string="Firmware Version")
    batch_no = fields.Char(string="Batch No ")
    manf = fields.Many2one('manufacturer',string="Manufacturer ")
    originc = fields.Many2one('country',string="Country of Origin ")
    prodDate = fields.Date(string="Production Date ")
    expDate = fields.Date(string="Expiry Date")
    supplier_invoice_no = fields.Char(string="Supplier Invoice No.")
    priority=fields.Integer(string="Priority.")
    barrel = fields.Integer(string="No of Barrels.")
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

class QualityTestType(models.Model):
    _name = "quality.test.type"

    code = fields.Char(string="Test code.")
    name = fields.Char(string="Test Name.")
    desc = fields.Char(string="Test Description.")

class QualityTestType(models.Model):
    _name = "quality.test"

    quality_test_type_id = fields.Many2one('quality.test.type')
    quality_test_name=fields.Char(related='quality_test_type_id.name')
    quality_test_code= fields.Char(related='quality_test_type_id.code')
    quality_test_desc = fields.Char(related='quality_test_type_id.desc')
    result=fields.Char('Result')
    quality_check_id=fields.Many2one("quality.check")


class QualityCheckUpdate(models.Model):
    _inherit = "quality.check"

    reanalysisDate = fields.Date(string="Reanalysis Date")
    remark = fields.Char(string="Remark.")
    quality_tests = fields.One2many('quality.test','quality_check_id')

    def do_pass(self):
        self.lot_id.qc_no=self.name
        self.lot_id.name=self.name+"("+self.lot_id.batch_no+")"
        self.write({'quality_state': 'pass',
                    'user_id': self.env.user.id,
                    'control_date': datetime.now()})
        if self.env.context.get('no_redirect'):
            return True
        return self.redirect_after_pass_fail()


    def do_fail(self):
        self.lot_id.qc_no = self.name
        self.lot_id.name = self.name + "(" + self.lot_id.batch_no + ")"

        self.write({
            'quality_state': 'fail',
            'user_id': self.env.user.id,
            'control_date': datetime.now()})
        if self.env.context.get('no_redirect'):
            return True
        return self.redirect_after_pass_fail()
