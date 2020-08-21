from odoo.exceptions import Warning
from odoo import models, fields, api, _


class DosageForm(models.Model):
    _name = 'product.dosageform'
    _description = 'Dosage Form'

    name = fields.Char("Dosage Form")


class ProductionLine(models.Model):
    _name = 'product.productionline'
    _description = 'Production Line'

    name = fields.Char("Production Line")

class StoreType(models.Model):
    _name = 'product.storetype'
    _description = 'Store Type'

    name = fields.Char("Store Type")

class Classification(models.Model):
    _name = 'product.classification'
    _description = 'Classification'

    name = fields.Char("Classification")
    sub_classifications=fields.One2many('product.subclassification','classification_id')

class SubClassification(models.Model):
    _name = 'product.subclassification'
    _description = 'Sub Classification'

    name = fields.Char("Sub Classification")
    classification_id=fields.Many2one('product.classification',"Classification")


class ProductUpdate(models.Model):
    _inherit = 'product.template'

    shelf_life = fields.Integer("Shelf life")
    dosage_form = fields.Many2one('product.dosageform')
    production_line = fields.Many2one('product.productionline')
    batch_no=fields.Char("Batch No")
    is_packaging=fields.Boolean("Packaging Product",default=False)
    classification_id = fields.Many2one('product.classification')
    sub_classification_id = fields.Many2one('product.subclassification')
    store_type_id = fields.Many2one('product.storetype')
    min_available=fields.Float('Min')
    generic_name=fields.Char("Generic Name: ")
    spec_doc_no = fields.Char("SpecDocNo: ")