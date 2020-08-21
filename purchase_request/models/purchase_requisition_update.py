# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
import datetime

from odoo import _, api, exceptions, fields, models


class PurchaseDeliveryplace(models.Model):

    _name = 'purchase.deliveryplace'
    _description = 'Delivery place'
    name = fields.Char(string='Delivery Place')

class PurchaseShippingby(models.Model):

    _name = 'purchase.shippingby'
    _description = 'Shipping by'
    name = fields.Char(string='Shipping By')


class PurchasePacking(models.Model):

    _name = 'purchase.packing'
    _description = 'Packing'
    name = fields.Char(string='Packing')

class PurchasePortofloading(models.Model):

    _name = 'purchase.portofloading'
    _description = 'Port of loading'
    name = fields.Char(string='Port of loading')


class PurchasePortofdestination(models.Model):

    _name = 'purchase.portofdestination'
    _description = 'Port of destination'
    name = fields.Char(string='Port of Destination')


class PurchaseRequisition(models.Model):
    _inherit = "purchase.agreement"

    deliveryplace = fields.Many2one('purchase.deliveryplace', string="Delivery place")
    shippingby = fields.Many2one('purchase.shippingby', string="Shipping by")
    packing = fields.Many2one('purchase.packing', string="Packing")
    portofloading = fields.Many2one('purchase.portofloading', string="Port loading")
    portofdestination = fields.Many2one('purchase.portofdestination', string="Port Destination")
    purchase_source_type = fields.Selection([
        ('local', 'Local Purchase'),
        ('foreign', 'Foreign Purchase'),
    ], default='local', string="Purchase Type")

class ChequePayment(models.Model):
        _name = 'purchase.chequepayment'
        _description = 'Cheque payment request form'
        _inherit = ['mail.thread', 'mail.activity.mixin']

        @api.model
        def _get_default_requested_by(self):
            return self.env["res.users"].browse(self.env.uid)

        name = fields.Char(string='Payment reason')
        vendor_id = fields.Many2one('res.partner', 'Pay to')
        requested_id = fields.Many2one('res.users', 'Requested By',default=_get_default_requested_by,)
        verified_id = fields.Many2one('res.users', 'Verified By',readonly='true')
        amount = fields.Float('Amount')
        remark = fields.Char('Remark')

        date_requested = fields.Date(string='Date Requested',readonly='true')
        date_approved=fields.Date('Date approved',readonly='true')

        state = fields.Selection([
            ('draft', 'Draft'), ('approve', 'Approved'),
            ('verify', 'Verified'),('reject', 'Rejected')],
            string='Status', default='draft', readonly=True, required=True, copy=False)

        def button_draft(self):
            self.write({'state': 'draft'})

        def button_approve(self):
            self.write({'state': 'approve'})
            self.date_requested = datetime.datetime.now()

        def button_verify(self):
            self.write({'state': 'verify'})
            self.verified_id=self.env["res.users"].browse(self.env.uid)
            self.date_approved = datetime.datetime.now()
