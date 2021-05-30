# Copyright 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import UserError


class MrpAbstractWorkorder(models.AbstractModel):
    _inherit = "mrp.abstract.workorder"

    product_id = fields.Many2one(related='production_id.product_id',  store=True, check_company=True)



class MrpProduction(models.Model):
    _inherit = "mrp.production"

    has_master_batch=fields.Boolean("Has Master Batch")
    product_master_batch_id=fields.Many2one('product.product') #, domain="[('categ_id.name', '=', 'MasterBatch')]"
    master_batch_percentage=fields.Float("Master Batch Percentage")
    pet_qty=fields.Float("Pet size")

    def post_inventory(self):
        for order in self:
            #gets the list of raw material that are done (state is done is filtered out to the resulting variable)
            moves_not_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done')
            # gets the list of raw material not done(state other than done is filtered out to the resulting variable)
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            #
            for move in moves_to_do.filtered(lambda m: m.product_qty == 0.0 and m.quantity_done > 0):
                move.product_uom_qty = move.quantity_done
            # MRP do not merge move, catch the result of _action_done in order
            # to get extra moves.
            moves_to_do = moves_to_do._action_done()
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done') - moves_not_to_do
            order._cal_price(moves_to_do)
            moves_to_finish = order.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves_to_finish = moves_to_finish._action_done()
            order.workorder_ids.mapped('raw_workorder_line_ids').unlink()
            order.workorder_ids.mapped('finished_workorder_line_ids').unlink()
            order.action_assign()
            consume_move_lines = moves_to_do.mapped('move_line_ids')
            for moveline in moves_to_finish.mapped('move_line_ids'):
                if moveline.move_id.has_tracking != 'none' and moveline.product_id == order.product_id or moveline.lot_id in consume_move_lines.mapped(
                        'lot_produced_ids'):
                    if any([not ml.lot_produced_ids for ml in consume_move_lines]):
                        raise UserError(('You can not consume without telling for which lot you consumed it'))
                    # Link all movelines in the consumed with same lot_produced_ids false or the correct lot_produced_ids
                    filtered_lines = consume_move_lines.filtered(lambda ml: moveline.lot_id in ml.lot_produced_ids)
                    moveline.write({'consume_line_ids': [(6, 0, [x for x in filtered_lines.ids])]})
                else:
                    # Link with everything
                    moveline.write({'consume_line_ids': [(6, 0, [x for x in consume_move_lines.ids])]})
        return True

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.product_qty = self.bom_id.product_qty
        self.product_uom_id = self.bom_id.product_uom_id.id
        self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]
        self.picking_type_id = self.bom_id.picking_type_id or self.picking_type_id

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id','product_master_batch_id','master_batch_percentage','has_master_batch')
    def _onchange_move_raw(self):
        if self.bom_id and self.product_qty > 0:
            # keep manual entries by using filtered get a recordset removing the newly added on the table
            list_move_raw = [(4, move.id) for move in self.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
            list_move_raw.append((5, 0, 0))
            #get the default bom lines and create a stock move for them
            moves_raw_values = self._get_moves_raw_values()
            #first using the filtered filter the ones found on the bom then loop and collect the bomlineid's
            move_raw_dict = {move.bom_line_id.id: move for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)}
            move_raw_dict={}
            #loop the moves created based on the original bom
            for move_raw_values in moves_raw_values:
                #the newly created moves based on the bomlines do have the bomline id so check if that is found on the already written on the table if so update it
                if move_raw_values['bom_line_id'] in move_raw_dict:
                    # update existing entries
                    list_move_raw += [(1, move_raw_dict[move_raw_values['bom_line_id']].id, move_raw_values)]
                else:
                    # add new entries
                    list_move_raw += [(0, 0, move_raw_values)]
            self.move_raw_ids = list_move_raw
        else:
            self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]

    #
    def _get_moves_raw_values(self):
        moves = []
        for production in self:
            #trying to get the bom lines of a specific bomid by exploding it and creating a stock.move by calling get_move_raw_values for it
            factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
            boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
            for bom_line, line_data in lines:
                if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
                        bom_line.product_id.type not in ['product', 'consu']:
                    continue
                moves.append(production._get_move_raw_values(bom_line, line_data))
                if bom_line['purge_allowance']>0:
                    moves.append(production._get_purge_reject_values(bom_line, line_data,1))

                if bom_line['reject_allowance']>0:
                    moves.append(production._get_purge_reject_values(bom_line, line_data,2))

        if self.has_master_batch and self.product_master_batch_id:
             moves.append(production._additional_masterbatch())
        return moves

    #prepare the moves
    def _get_purge_reject_values(self, bom_line, line_data,purge_reject):
        quantity = line_data['qty']
        name=""
        if purge_reject==1:
            percent=bom_line['purge_allowance']
            name
        else:
            percent=bom_line['reject_allowance']
        quantity=quantity*(percent/100)
        if self.has_master_batch:
            quantity=quantity-quantity*(self.master_batch_percentage/100)
        # alt_op needed for the case when you explode phantom bom and all the lines will be consumed in the operation given by the parent bom line
        alt_op = line_data['parent_line'] and line_data['parent_line'].operation_id.id or False
        source_location = self.location_src_id
        data = {
            'sequence': bom_line.sequence,
            'name': self.name,
            'reference': self.name,
            'date': self.date_planned_start,
            'date_expected': self.date_planned_start,
            'bom_line_id': 0,
            'picking_type_id': self.picking_type_id.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.with_context(force_company=self.company_id.id).property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': bom_line.operation_id.id or alt_op,
            'price_unit': bom_line.product_id.standard_price,
            'procure_method': 'make_to_stock',
            'origin': self.name,
            'state': 'draft',
            'warehouse_id': source_location.get_warehouse().id,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
        }
        return data

    #prepare the moves
    def _get_move_raw_values(self, bom_line, line_data):
        quantity = line_data['qty']
        self.pet_qty=quantity
        if self.has_master_batch:
            quantity=quantity-quantity*(self.master_batch_percentage/100)
        # alt_op needed for the case when you explode phantom bom and all the lines will be consumed in the operation given by the parent bom line
        alt_op = line_data['parent_line'] and line_data['parent_line'].operation_id.id or False
        source_location = self.location_src_id
        data = {
            'sequence': bom_line.sequence,
            'name': self.name,
            'reference': self.name,
            'date': self.date_planned_start,
            'date_expected': self.date_planned_start,
            'bom_line_id': bom_line.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.with_context(force_company=self.company_id.id).property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': bom_line.operation_id.id or alt_op,
            'price_unit': bom_line.product_id.standard_price,
            'procure_method': 'make_to_stock',
            'origin': self.name,
            'state': 'draft',
            'warehouse_id': source_location.get_warehouse().id,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
        }
        return data

    #prepare the moves
    def _additional_masterbatch(self):
        # alt_op needed for the case when you explode phantom bom and all the lines will be consumed in the operation given by the parent bom line
        source_location = self.location_src_id
        data = {
            'sequence': "",
            'name': self.name,
            'reference': self.name,
            'date': self.date_planned_start,
            'date_expected': self.date_planned_start,
            'bom_line_id': 1,
            'picking_type_id': self.picking_type_id.id,
            'product_id': self.product_master_batch_id.id,
            'product_uom_qty': self.pet_qty*(self.master_batch_percentage/100),
            'product_uom': self.product_master_batch_id.uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.with_context(force_company=self.company_id.id).property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': 1,
            'price_unit': self.product_master_batch_id.price,
            'procure_method': 'make_to_stock',
            'origin': self.name,
            'state': 'draft',
            'warehouse_id': source_location.get_warehouse().id,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
        }
        return data


    mrp_production_request_id = fields.Many2one(
        comodel_name="mrp.production.request",
        string="Manufacturing Request",
        copy=False,
        readonly=True,
    )

    def _generate_finished_moves(self):
        """`move_dest_ids` is a One2many fields in mrp.production, thus we
        cannot indicate the same destination move in several MOs (which most
        probably would be the case with MRs).
        Storing them on the MR and writing them on the finished moves as it
        would happen if they were present in the MO, is the best workaround
        without changing the standard data model."""
        move = super()._generate_finished_moves()
        request = self.mrp_production_request_id
        if request and request.move_dest_ids:
            move.write({"move_dest_ids": [(4, x.id) for x in request.move_dest_ids]})
        return move

    def second_produce_product(self):
        self.ensure_one()
        self.post_inventory()
        if self.bom_id.type == 'phantom':
            raise UserError('You cannot produce a MO with a bom kit product.')
        action = self.env.ref('mrp_production_request.act_mrp_second_product_produce').read()[0]
        return action

    def rejected_produce_product(self):
        self.ensure_one()
        self.post_inventory()
        if self.bom_id.type == 'phantom':
            raise UserError('You cannot produce a MO with a bom kit product.')
        action = self.env.ref('mrp_production_request.act_mrp_rejected_product_produce').read()[0]
        return action

    def purge_produce_product(self):
        self.ensure_one()
        self.post_inventory()
        if self.bom_id.type == 'phantom':
            raise UserError('You cannot produce a MO with a bom kit product.')
        action = self.env.ref('mrp_production_request.act_mrp_purge_product_produce').read()[0]
        return action
