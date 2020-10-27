# Copyright 2018 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from odoo import _, api, fields, models
from odoo.exceptions import UserError
class StockPicking(models.Model):
    _inherit = "stock.picking"

    received_by_id = fields.Many2one('hr.employee', 'Verified By')
    picking_code = fields.Char("The code",related='picking_type_id.sequence_code')
    production_idz=fields.Char("Production No:")
    employee_id=fields.Many2one('hr.employee',"Requested By")
    department_name=fields.Char("Requesting Department :")
    section_name = fields.Char("Requesting Section :")

    product_idz=fields.Many2one('product.product',"Product")
    product_code=fields.Char('Product Code')
    batch_size=fields.Float("Batch Size")
    production_batch_no = fields.Char("Batch No:")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Verified'),
        ('received', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    @api.onchange('user_id')
    def userchanged(self):
        selected_employee = self.env['hr.employee'].search(
            [('user_id', '=', self.user_id.id)])
        for x in selected_employee:
            self.employee_id=x.id
            self.department_name=x.department_id.name
    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        for picking in self:
            if not picking.move_lines:
                picking.state = 'draft'
            elif any(move.state == 'draft' for move in picking.move_lines):  # TDE FIXME: should be all ?
                picking.state = 'draft'
            elif all(move.state == 'cancel' for move in picking.move_lines):
                picking.state  = 'cancel'
            elif all(move.state in ['cancel', 'done'] for move in picking.move_lines):
                picking.state = 'done'
            else:
                relevant_move_state = picking.move_lines._get_relevant_state_among_moves()
                if relevant_move_state == 'partially_available':
                    picking.state = 'assigned'
                else:
                    picking.state = relevant_move_state

    store_request_id=fields.Many2one('store.request',"Store request")
    @api.model
    def _purchase_request_picking_confirm_message_content(
        self, picking, request, request_dict
    ):
        if not request_dict:
            request_dict = {}
        title = _("Receipt confirmation %s for your Request %s") % (
            picking.name,
            request.name,
        )
        message = "<h3>%s</h3>" % title
        message += _(
            "The following requested items from Purchase Request %s "
            "have now been received in Incoming Shipment %s:"
        ) % (request.name, picking.name)
        message += "<ul>"
        for line in request_dict.values():
            message += _("<li><b>%s</b>: Received quantity %s %s</li>") % (
                line["name"],
                line["product_qty"],
                line["product_uom"],
            )
        message += "</ul>"
        return message
    def button_received(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1)

        self.received_by_id=employee.id
        self.state="received"
        return
    def action_done(self):
        super(StockPicking, self).action_done()
        request_obj = self.env["purchase.request"]
        for picking in self:
            requests_dict = {}
            if picking.picking_type_id.code != "incoming":
                continue
            for move in picking.move_lines:
                if move.purchase_line_id:
                    for (
                        request_line
                    ) in move.purchase_line_id.sudo().purchase_request_lines:
                        request_id = request_line.request_id.id
                        if request_id not in requests_dict:
                            requests_dict[request_id] = {}
                        data = {
                            "name": request_line.name,
                            "product_qty": move.product_qty,
                            "product_uom": move.product_uom.name,
                        }
                        requests_dict[request_id][request_line.id] = data
            for request_id in requests_dict:
                request = request_obj.sudo().browse(request_id)
                message = self._purchase_request_picking_confirm_message_content(
                    picking, request, requests_dict[request_id]
                )
                request.sudo().message_post(
                    body=message,
                    subtype="mail.mt_comment",
                    author_id=self.env.user.partner_id.id,
                )

class ReturnPickingUpdate(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        if self.picking_id and self.picking_id.state != 'received':

            raise UserError(_("You may only return Receivied pickings."))
        for move in self.picking_id.move_lines:
            if move.state == 'cancel':
                continue
            if move.scrapped:
                continue
            if move.move_dest_ids:
                move_dest_exists = True
            product_return_moves.append((0, 0, self._prepare_stock_return_picking_line_vals_from_move(move)))
        if self.picking_id and not product_return_moves:
            raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
            self.original_location_id = self.picking_id.location_id.id
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id
