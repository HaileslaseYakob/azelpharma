# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PFIDocuments(models.Model):
    _name = 'purchase.checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Purchase Checklist"
    _order = 'sequence'

    name = fields.Char(string='Name', copy=False, required=1, help="Checklist Name")
    document_type = fields.Selection([('entry', 'PFI'),
                                      ('other', 'Other')], string='Checklist Type', help='Type of Checklist', required=1)
    sequence = fields.Integer('Sequence')


class HrEmployeeDocumentInherit(models.Model):
    _inherit = 'purchase.order.document'

    document_name = fields.Many2one('purchase.checklist', string='Document', help='Type of Document', required=True)

