from odoo.exceptions import Warning
from odoo import models, fields, api, _


class EventCustomize(models.Model):
    _inherit = 'event.event'


    department_id = fields.Many2one('hr.department', string="Requesting Department", help="Training requesting department")

