# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class PurchaseOrderDocument(models.Model):
    _name = 'purchase.order.document'
    _description = 'Purchase Documents'

    name = fields.Char(string='Document Number', required=True, copy=False, help='You can give your'
                                                                                 'Document number.')
    description = fields.Text(string='Description', copy=False, help="Description")
    purchase_ref = fields.Many2one('purchase.order', invisible=1, copy=False)
    purchase_attachment_id = fields.Many2many('ir.attachment', 'purchase_doc_attach_rel', 'doc_id', 'attach_id3', string="Attachment",
                                         help='You can attach the copy of your document', copy=False)
    issue_date = fields.Date(string='Issue Date', default=fields.datetime.now(), help="Date of issue", copy=False)
    document_type = fields.Many2one('document.type', string="Document Type", help="Document type")
   

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _document_count(self):
        for each in self:
            document_ids = self.env['purchase.order.document'].sudo().search([('purchase_ref', '=', each.id)])
            each.document_count = len(document_ids)

    def document_view(self):
        self.ensure_one()
        domain = [
            ('purchase_ref', '=', self.id)]
        return {
            'name': _('Documents'),
            'domain': domain,
            'res_model': 'purchase.order.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_purchase_ref': %s}" % self.id
        }

    document_count = fields.Integer(compute='_document_count', string='# Documents')


class PurchaseOrderAttachment(models.Model):
    _inherit = 'ir.attachment'

    purchase_doc_attach_rel = fields.Many2many('purchase.order.document', 'purchase_attachment_id', 'attach_id3', 'doc_id',
                                      string="Attachment", invisible=1)
    purchase_attach_rel = fields.Many2many('purchase.document', 'attach_id', 'attachment_id', 'document_id',
                                  string="Attachment", invisible=1)
