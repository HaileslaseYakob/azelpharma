# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, exceptions, fields, models


class SaleOrderUpdate(models.Model):
    _inherit = "sale.order"

    vehicle_transfer_plateno=fields.Char("Vehicle Plate no.")