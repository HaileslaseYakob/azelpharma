# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round

class MrpProductProduceUpdate(models.TransientModel):
    _description = "Record Production"
    _inherit = ["mrp.product.produce"]

    def _update_workorder_lines(self):
        """ Update workorder lines, according to the new qty currently
        produced. It returns a dict with line to create, update or delete.
        It do not directly write or unlink the line because this function is
        used in onchange and request that write on db (e.g. workorder creation).
        """
        line_values = {'to_create': [], 'to_delete': [], 'to_update': {}}
        # moves are actual records
        move_finished_ids = self.move_finished_ids._origin.filtered(lambda move: move.product_id != self.product_id and move.state not in ('done', 'cancel'))
        move_raw_ids = self.move_raw_ids._origin.filtered(lambda move: move.state not in ('done', 'cancel'))
        move_raw_ids = move_raw_ids.filtered(lambda m:not m.bom_line_id.id == False)
        for move in move_raw_ids | move_finished_ids:
            move_workorder_lines = self._workorder_line_ids().filtered(lambda w: w.move_id == move)

            # Compute the new quantity for the current component
            rounding = move.product_uom.rounding
            new_qty = self._prepare_component_quantity(move, self.qty_producing)

            # In case the production uom is different than the workorder uom
            # it means the product is serial and production uom is not the reference
            new_qty = self.product_uom_id._compute_quantity(
                new_qty,
                self.production_id.product_uom_id,
                round=False
            )
            qty_todo = float_round(new_qty - sum(move_workorder_lines.mapped('qty_to_consume')), precision_rounding=rounding)

            # Remove or lower quantity on exisiting workorder lines
            if float_compare(qty_todo, 0.0, precision_rounding=rounding) < 0:
                qty_todo = abs(qty_todo)
                # Try to decrease or remove lines that are not reserved and
                # partialy reserved first. A different decrease strategy could
                # be define in _unreserve_order method.
                for workorder_line in move_workorder_lines.sorted(key=lambda wl: wl._unreserve_order()):
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    # If the quantity to consume on the line is lower than the
                    # quantity to remove, the line could be remove.
                    if float_compare(workorder_line.qty_to_consume, qty_todo, precision_rounding=rounding) <= 0:
                        qty_todo = float_round(qty_todo - workorder_line.qty_to_consume, precision_rounding=rounding)
                        if line_values['to_delete']:
                            line_values['to_delete'] |= workorder_line
                        else:
                            line_values['to_delete'] = workorder_line
                    # decrease the quantity on the line
                    else:
                        new_val = workorder_line.qty_to_consume - qty_todo
                        # avoid to write a negative reserved quantity
                        new_reserved = max(0, workorder_line.qty_reserved - qty_todo)
                        line_values['to_update'][workorder_line] = {
                            'qty_to_consume': new_val,
                            'qty_done': new_val,
                            'qty_reserved': new_reserved,
                        }
                        qty_todo = 0
            else:
                # Search among wo lines which one could be updated
                qty_reserved_wl = defaultdict(float)
                # Try to update the line with the greater reservation first in
                # order to promote bigger batch.
                for workorder_line in move_workorder_lines.sorted(key=lambda wl: wl.qty_reserved, reverse=True):
                    rounding = workorder_line.product_uom_id.rounding
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    move_lines = workorder_line._get_move_lines()
                    qty_reserved_wl[workorder_line.lot_id] += workorder_line.qty_reserved
                    # The reserved quantity according to exisiting move line
                    # already produced (with qty_done set) and other production
                    # lines with the same lot that are currently on production.
                    qty_reserved_remaining = sum(move_lines.mapped('product_uom_qty')) - sum(move_lines.mapped('qty_done')) - qty_reserved_wl[workorder_line.lot_id]
                    if float_compare(qty_reserved_remaining, 0, precision_rounding=rounding) > 0:
                        qty_to_add = min(qty_reserved_remaining, qty_todo)
                        line_values['to_update'][workorder_line] = {
                            'qty_done': workorder_line.qty_to_consume + qty_to_add,
                            'qty_to_consume': workorder_line.qty_to_consume + qty_to_add,
                            'qty_reserved': workorder_line.qty_reserved + qty_to_add,
                        }
                        qty_todo -= qty_to_add
                        qty_reserved_wl[workorder_line.lot_id] += qty_to_add

                    # If a line exists without reservation and without lot. It
                    # means that previous operations could not find any reserved
                    # quantity and created a line without lot prefilled. In this
                    # case, the system will not find an existing move line with
                    # available reservation anymore and will increase this line
                    # instead of creating a new line without lot and reserved
                    # quantities.
                    if not workorder_line.qty_reserved and not workorder_line.lot_id and workorder_line.product_tracking != 'serial':
                        line_values['to_update'][workorder_line] = {
                            'qty_done': workorder_line.qty_to_consume + qty_todo,
                            'qty_to_consume': workorder_line.qty_to_consume + qty_todo,
                        }
                        qty_todo = 0

                # if there are still qty_todo, create new wo lines
                if float_compare(qty_todo, 0.0, precision_rounding=rounding) > 0:
                    for values in self._generate_lines_values(move, qty_todo):
                        line_values['to_create'].append(values)
        return line_values



class MrpProductProduce(models.TransientModel):
    _name = "mrp.second.product.produce"
    _description = "Record Production"
    _inherit = ["mrp.abstract.workorder"]

    @api.model
    def default_get(self, fields):
        res = super(MrpProductProduce, self).default_get(fields)
        production = self.env['mrp.production']
        production_id = self.env.context.get('default_production_id') or self.env.context.get('active_id')
        if production_id:
            production = self.env['mrp.production'].browse(production_id)
        if production.exists():
            serial_finished = (production.product_id.tracking == 'serial')
            todo_uom = production.product_uom_id.id
            todo_quantity = self._get_todo(production)
            if serial_finished:
                todo_quantity = 1.0
                if production.product_uom_id.uom_type != 'reference':
                    todo_uom = self.env['uom.uom'].search([('category_id', '=', production.product_uom_id.category_id.id), ('uom_type', '=', 'reference')]).id
            if 'production_id' in fields:
                res['production_id'] = production.id
            if 'product_id' in fields:
                res['product_id'] = production.product_id.id
            if 'product_uom_id' in fields:
                res['product_uom_id'] = todo_uom
            if 'serial' in fields:
                res['serial'] = bool(serial_finished)
            if 'qty_producing' in fields:
                res['qty_producing'] = todo_quantity
            if 'consumption' in fields:
                res['consumption'] = production.bom_id.consumption
        return res



    def _update_workorder_lines(self):
        """ Update workorder lines, according to the new qty currently
        produced. It returns a dict with line to create, update or delete.
        It do not directly write or unlink the line because this function is
        used in onchange and request that write on db (e.g. workorder creation).
        """
        line_values = {'to_create': [], 'to_delete': [], 'to_update': {}}
        # moves are actual records
        move_finished_ids = self.move_finished_ids._origin.filtered(lambda move: move.product_id != self.product_id and move.state not in ('done', 'cancel'))
        move_raw_ids = self.move_raw_ids._origin.filtered(lambda move: move.state not in ('done', 'cancel'))
        move_raw_ids = move_raw_ids.filtered(lambda m:not m.bom_line_id.id == False)
        for move in move_raw_ids | move_finished_ids:
            move_workorder_lines = self._workorder_line_ids().filtered(lambda w: w.move_id == move)

            # Compute the new quantity for the current component
            rounding = move.product_uom.rounding
            new_qty = self._prepare_component_quantity(move, self.qty_producing)

            # In case the production uom is different than the workorder uom
            # it means the product is serial and production uom is not the reference
            new_qty = self.product_uom_id._compute_quantity(
                new_qty,
                self.production_id.product_uom_id,
                round=False
            )
            qty_todo = float_round(new_qty - sum(move_workorder_lines.mapped('qty_to_consume')), precision_rounding=rounding)

            # Remove or lower quantity on exisiting workorder lines
            if float_compare(qty_todo, 0.0, precision_rounding=rounding) < 0:
                qty_todo = abs(qty_todo)
                # Try to decrease or remove lines that are not reserved and
                # partialy reserved first. A different decrease strategy could
                # be define in _unreserve_order method.
                for workorder_line in move_workorder_lines.sorted(key=lambda wl: wl._unreserve_order()):
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    # If the quantity to consume on the line is lower than the
                    # quantity to remove, the line could be remove.
                    if float_compare(workorder_line.qty_to_consume, qty_todo, precision_rounding=rounding) <= 0:
                        qty_todo = float_round(qty_todo - workorder_line.qty_to_consume, precision_rounding=rounding)
                        if line_values['to_delete']:
                            line_values['to_delete'] |= workorder_line
                        else:
                            line_values['to_delete'] = workorder_line
                    # decrease the quantity on the line
                    else:
                        new_val = workorder_line.qty_to_consume - qty_todo
                        # avoid to write a negative reserved quantity
                        new_reserved = max(0, workorder_line.qty_reserved - qty_todo)
                        line_values['to_update'][workorder_line] = {
                            'qty_to_consume': new_val,
                            'qty_done': new_val,
                            'qty_reserved': new_reserved,
                        }
                        qty_todo = 0
            else:
                # Search among wo lines which one could be updated
                qty_reserved_wl = defaultdict(float)
                # Try to update the line with the greater reservation first in
                # order to promote bigger batch.
                for workorder_line in move_workorder_lines.sorted(key=lambda wl: wl.qty_reserved, reverse=True):
                    rounding = workorder_line.product_uom_id.rounding
                    if float_compare(qty_todo, 0, precision_rounding=rounding) <= 0:
                        break
                    move_lines = workorder_line._get_move_lines()
                    qty_reserved_wl[workorder_line.lot_id] += workorder_line.qty_reserved
                    # The reserved quantity according to exisiting move line
                    # already produced (with qty_done set) and other production
                    # lines with the same lot that are currently on production.
                    qty_reserved_remaining = sum(move_lines.mapped('product_uom_qty')) - sum(move_lines.mapped('qty_done')) - qty_reserved_wl[workorder_line.lot_id]
                    if float_compare(qty_reserved_remaining, 0, precision_rounding=rounding) > 0:
                        qty_to_add = min(qty_reserved_remaining, qty_todo)
                        line_values['to_update'][workorder_line] = {
                            'qty_done': workorder_line.qty_to_consume + qty_to_add,
                            'qty_to_consume': workorder_line.qty_to_consume + qty_to_add,
                            'qty_reserved': workorder_line.qty_reserved + qty_to_add,
                        }
                        qty_todo -= qty_to_add
                        qty_reserved_wl[workorder_line.lot_id] += qty_to_add

                    # If a line exists without reservation and without lot. It
                    # means that previous operations could not find any reserved
                    # quantity and created a line without lot prefilled. In this
                    # case, the system will not find an existing move line with
                    # available reservation anymore and will increase this line
                    # instead of creating a new line without lot and reserved
                    # quantities.
                    if not workorder_line.qty_reserved and not workorder_line.lot_id and workorder_line.product_tracking != 'serial':
                        line_values['to_update'][workorder_line] = {
                            'qty_done': workorder_line.qty_to_consume + qty_todo,
                            'qty_to_consume': workorder_line.qty_to_consume + qty_todo,
                        }
                        qty_todo = 0

                # if there are still qty_todo, create new wo lines
                if float_compare(qty_todo, 0.0, precision_rounding=rounding) > 0:
                    for values in self._generate_lines_values(move, qty_todo):
                        line_values['to_create'].append(values)
        return line_values

    serial = fields.Boolean('Requires Serial')
    product_tracking = fields.Selection(related="product_id.tracking")
    is_pending_production = fields.Boolean(compute='_compute_pending_production')

    move_raw_ids = fields.One2many(related='production_id.move_raw_ids', string="PO Components")
    move_finished_ids = fields.One2many(related='production_id.move_finished_ids')

    raw_workorder_line_ids = fields.One2many('mrp.second.product.produce.line',
        'raw_product_produce_id', string='Components')
    finished_workorder_line_ids = fields.One2many('mrp.second.product.produce.line',
        'finished_product_produce_id', string='By-products')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',
        required=True, ondelete='cascade')
    #
    @api.depends('qty_producing')
    def _compute_pending_production(self):
        """ Compute if it exits remaining quantity once the quantity on the
        current wizard will be processed. The purpose is to display or not
        button 'continue'.
        """
        # company_id = self.env.context.get('default_company_id', self.env.company.id)
        # return self.env['stock.picking.type'].search([
        #     ('code', '=', 'mrp_operation'),
        #     ('warehouse_id.company_id', '=', company_id),
        # ], limit=1).id
        if self.production_id.product_id.product_second:
            self.product_id = self.production_id.product_id.product_second
        else:
           product_new = self.env['product.product'].create({
                'name': self.product_id.name+"-Second",
                'type': 'product',
                'weight': 0,
                'uom_id': self.product_id.uom_id.id,
            })
           self.product_id.product_second=product_new.id
           self.product_id = product_new.id
           # test_product_delivery_inv_template = self.env['product.template'].create({
        #     'name': 'Test product template invoiced on delivery',
        #     'type': 'product',
        #     'categ_id': self.test_product_category.id,
        #     'uom_id': uom.id,
        #     'uom_po_id': uom.id,
        # })
        for product_produce in self:
            remaining_qty = product_produce._get_todo(product_produce.production_id)
            product_produce.is_pending_production = remaining_qty - product_produce.qty_producing > 0.0

    def continue_production(self):
        """ Save current wizard and directly opens a new. """
        self.ensure_one()
        self._record_production()
        action = self.production_id.open_produce_product()
        action['context'] = {'default_production_id': self.production_id.id}
        return action

    def action_generate_serial(self):
        self.ensure_one()
        product_produce_wiz = self.env.ref('mrp.view_mrp_product_produce_wizard', False)
        self.finished_lot_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.production_id.company_id.id
        })
        return {
            'name': _('Produce'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.second.product.produce',
            'res_id': self.id,
            'view_id': product_produce_wiz.id,
            'target': 'new',
        }

    def do_produce(self):
        """ Save the current wizard and go back to the MO. """
        self.ensure_one()
        self._record_production()
        self._check_company()
        return {'type': 'ir.actions.act_window_close'}

    def _get_todo(self, production):
        """ This method will return remaining todo quantity of production. """
        main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
        todo_quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
        todo_quantity = todo_quantity if (todo_quantity > 0) else 0
        return todo_quantity

    def _record_production(self):
        # Check all the product_produce line have a move id (the user can add product
        # to consume directly in the wizard)
        for line in self._workorder_line_ids():
            if not line.move_id:
                # Find move_id that would match
                if line.raw_product_produce_id:
                    moves = self.move_raw_ids
                else:
                    moves = self.move_finished_ids
                move_id = moves.filtered(lambda m: m.product_id == line.product_id and m.state not in ('done', 'cancel'))
                if not move_id:
                    # create a move to assign it to the line
                    if line.raw_product_produce_id:
                        values = {
                            'name': self.production_id.name,
                            'reference': self.production_id.name,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom_id.id,
                            'location_id': self.production_id.location_src_id.id,
                            'location_dest_id': line.product_id.property_stock_production.id,
                            'raw_material_production_id': self.production_id.id,
                            'group_id': self.production_id.procurement_group_id.id,
                            'origin': self.production_id.name,
                            'state': 'confirmed',
                            'company_id': self.production_id.company_id.id,
                        }
                    else:
                        values = self.production_id._get_finished_move_value(line.product_id.id, 0, line.product_uom_id.id)
                    move_id = self.env['stock.move'].create(values)
                line.move_id = move_id.id

        # because of an ORM limitation (fields on transient models are not
        # recomputed by updates in non-transient models), the related fields on
        # this model are not recomputed by the creations above
        self.invalidate_cache(['move_raw_ids', 'move_finished_ids'])

        # Save product produce lines data into stock moves/move lines
        quantity = self.qty_producing
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_("The production order for '%s' has no quantity specified.") % self.product_id.display_name)
        self._update_finished_move()
        self._update_moves()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'date_start': datetime.now(),
            })
    def _get_finished_move_value(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        return {
            'product_id': product_id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom,
            'operation_id': operation_id,
            'byproduct_id': byproduct_id,
            'unit_factor': product_uom_qty / self.qty_producing,
            'name': self.production_id.name,
            'date': self.production_id.date_planned_start,
            'date_expected': self.production_id.date_planned_finished,
            'picking_type_id': self.production_id.picking_type_id.id,
            'location_id': self.product_id.with_context(force_company=self.company_id.id).property_stock_production.id,
            'location_dest_id': self.production_id.location_dest_id.id,
            'company_id': self.production_id.company_id.id,
            'production_id': self.production_id.id,
            'warehouse_id': self.production_id.location_dest_id.get_warehouse().id,
            'origin': self.production_id.name,
            'group_id': self.production_id.procurement_group_id.id,
            'propagate_cancel': self.production_id.propagate_cancel,
            'propagate_date': self.production_id.propagate_date,
            'propagate_date_minimum_delta': self.production_id.propagate_date_minimum_delta,
            'move_dest_ids': [(4, x.id) for x in self.production_id.move_dest_ids],
        }

    def gen_finished_moves(self):
        for line in self.raw_workorder_line_ids:
            values = {
                'name': self.production_id.name,
                'reference': self.production_id.name,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'location_id': self.production_id.location_src_id.id,
                'location_dest_id': line.product_id.property_stock_production.id,
                'raw_material_production_id': self.production_id.id,
                'group_id': self.production_id.procurement_group_id.id,
                'origin': self.production_id.name,
                'state': 'confirmed',
                'company_id': self.production_id.company_id.id,
            }
            move_id = self.env['stock.move'].create(values)
            self.env['stock.move.line'].create({
            'move_id': move_id.id,
            'lot_id': line.lot_id.id,
            'qty_done': line.qty_done,
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom_id.id,
            'location_id': move_id.location_id.id,
            'location_dest_id': move_id.location_dest_id.id,
            })

        moves_values = [self._get_finished_move_value(self.product_id.id, self.qty_producing,1)]

        moves = self.env['stock.move'].create(moves_values)
        self.env['stock.move.line'].create({
            'move_id': moves.id,
            'lot_id': self.finished_lot_id.id,
            'qty_done': self.qty_producing,
            'product_id': self.product_id.id,
            'product_uom_id': 1,
            'location_id': self.product_id.with_context(force_company=self.company_id.id).property_stock_production.id,
            'location_dest_id': self.production_id.location_dest_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}

class MrpProductProduceLine(models.TransientModel):
    _name = 'mrp.second.product.produce.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Record production line"

    raw_product_produce_id = fields.Many2one('mrp.second.product.produce', 'Component in Produce wizard')
    finished_product_produce_id = fields.Many2one('mrp.second.product.produce', 'Finished Product in Produce wizard')

    @api.model
    def _get_raw_workorder_inverse_name(self):
        return 'raw_product_produce_id'

    @api.model
    def _get_finished_workoder_inverse_name(self):
        return 'finished_product_produce_id'

    def _get_final_lots(self):
        product_produce_id = self.raw_product_produce_id or self.finished_product_produce_id
        return product_produce_id.finished_lot_id | product_produce_id.finished_workorder_line_ids.mapped('lot_id')

    def _get_production(self):
        product_produce_id = self.raw_product_produce_id or self.finished_product_produce_id
        return product_produce_id.production_id


