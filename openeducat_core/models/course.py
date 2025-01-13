# -*- coding: utf-8 -*-
###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OpCourse(models.Model):
    _name = "op.course"
    _inherit = "mail.thread"
    _description = "OpenEduCat Course"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', size=16, required=True)
    parent_id = fields.Many2one('op.course', 'Parent Course')
    evaluation_type = fields.Selection(
        [('normal', 'Normal'), ('GPA', 'GPA'),
         ('CWA', 'CWA'), ('CCE', 'CCE')],
        'Evaluation Type', default="normal", required=True)
    subject_ids = fields.Many2many('op.subject', string='Subject(s)')
    max_unit_load = fields.Float("Maximum Unit Load")
    min_unit_load = fields.Float("Minimum Unit Load")
    department_id = fields.Many2one(
        'op.department', 'Department',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    active = fields.Boolean(default=True)
    # branch_id = fields.Many2one('logic.branches', string="Branch")
    course_type = fields.Selection(
        [('indian', 'Indian'), ('international', 'International'), ('crash', 'Crash'), ('repeaters', 'Repeaters'),
         ('nil', 'Nil')], string="Type")

    related_product_id = fields.Many2one('product.product', string="Related Product")
    course_fee = fields.Float(string="Course Fee", related="related_product_id.list_price")
    product_added = fields.Boolean(string="Product Added")

    _sql_constraints = [
        ('unique_course_code',
         'unique(code)', 'Code should be unique per course!')]

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive Course.'))
        return True

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Courses'),
            'template': '/openeducat_core/static/xls/op_course.xls'
        }]

    def act_create_product(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Details'),
                'res_model': 'logic.product.details',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_name': self.name,
                            'default_course_id': self.id
                            }, }


class ProductDetails(models.TransientModel):
    _name = 'logic.product.details'

    name = fields.Char(string="Name")
    price = fields.Float(string="Price")
    course_id = fields.Many2one('op.course')

    def action_create_product(self):
        product = self.env['product.product'].sudo().create({
            'name': self.name,
            'list_price': self.price,
            'detailed_type': 'service',

        })
        self.course_id.related_product_id = product.id
        self.course_id.product_added = True
