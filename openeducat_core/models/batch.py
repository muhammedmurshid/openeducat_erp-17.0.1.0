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
from datetime import date


class OpBatch(models.Model):
    _name = "op.batch"
    _inherit = "mail.thread"
    _description = "OpenEduCat Batch"

    code = fields.Char('Code', size=16, required=True)
    name = fields.Char('Name', size=32, required=True)
    start_date = fields.Date(
        'Start Date', required=True, default=fields.Date.today())
    end_date = fields.Date('End Date', required=True)
    course_id = fields.Many2one('op.course', 'Course', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('up_coming', 'Up Coming')],
        string="Status", default='draft', tracking=True)
    remaining_days = fields.Integer(string="Remaining Days", compute="_compute_remaining_days", store=1)
    branch_id = fields.Many2one('logic.branches', string="Branch")
    admission_fee = fields.Integer(string="Admission Fee")
    course_fee = fields.Integer(string="Course Fee")
    student_ids = fields.One2many('logic.student.list', 'batch_id', )
    initiated_id = fields.Many2one('res.users', string="Initiated By")
    class_type = fields.Selection([('online', 'Online'), ('offline', 'Offline')], string="Class Type")
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('loan', 'Loan'), ('installment', 'Installment')],
                                string="Fee Type", default="lump_sum_fee", required=1)
    lump_fee_excluding_tax = fields.Float(string="Excluding Tax")
    lump_fee_including_tax = fields.Float(string="Including Tax")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id.id)
    total_lump_sum_fee = fields.Float(string="Total Fee", compute='_compute_total_lump_sum_fee', store=1)
    batch_type = fields.Selection(
        [('present_batch', 'Present Batch'), ('future_batch', 'Future Batch'), ],
        string="Type", default='present_batch', tracking=True)

    #lump sum plan offer
    term = fields.Char(string="Term")
    amount_exc_lump = fields.Float(string="Amount(Excluding Tax)")
    tax_amount_lump = fields.Float(string="Tax Amount")
    amount_inc_lump = fields.Float(string="Amount(Including Tax)", compute='_compute_amount_inc_lump', store=1)
    payment_date_lump = fields.Date(string="Payment Date")
    difference_in_fee_lump = fields.Float(string="Difference in fee", compute='_compute_amount_inc_lump', store=1)
    installment_ids = fields.One2many('payment.installment.type', 'installment_id')
    max_no_of_students = fields.Integer(string="Max no.of Students")
    @api.depends('student_ids')
    def _compute_total_students(self):
        for record in self:
            record.total_no_of_students = len(record.student_ids)

    total_no_of_students = fields.Integer(string="No. of Students", compute="_compute_total_students", store=True)

    @api.depends('amount_exc_lump','tax_amount_lump','amount_inc_lump','total_lump_sum_fee')
    def _compute_amount_inc_lump(self):
        for i in self:
            if i.tax_amount_lump != 0:
                i.amount_inc_lump = i.amount_exc_lump + i.tax_amount_lump
            if i.total_lump_sum_fee != 0 and i.amount_inc_lump !=0:
                i.difference_in_fee_lump = i.total_lump_sum_fee - i.amount_inc_lump

    @api.depends('lump_fee_including_tax','lump_fee_excluding_tax')
    def _compute_total_lump_sum_fee(self):
        for i in self:
            i.total_lump_sum_fee = i.lump_fee_excluding_tax + i.lump_fee_including_tax

    def act_confirm_batch(self):
        self.state = 'in_progress'
        print('hi')

    _sql_constraints = [
        ('unique_batch_code',
         'unique(code)', 'Code should be unique per batch!')]

    @api.depends('start_date', 'end_date')
    def _compute_remaining_days(self):
        for record in self:
            if record.start_date:
                today = date.today()
                if record.start_date <= today:
                    if record.end_date:
                        end_date = record.end_date
                        # Compute remaining days
                        remaining_days = (end_date - today).days
                        # Ensure no negative remaining days
                        record.remaining_days = max(remaining_days, 0)
                    else:
                        record.remaining_days = 0
                else:
                    record.remaining_days = 0

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            start_date = fields.Date.from_string(record.start_date)
            end_date = fields.Date.from_string(record.end_date)
            if start_date > end_date:
                raise ValidationError(
                    _("End Date cannot be set before Start Date."))

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self.env.context.get('get_parent_batch', False):
            lst = []
            lst.append(self.env.context.get('course_id'))
            courses = self.env['op.course'].browse(lst)
            while courses.parent_id:
                lst.append(courses.parent_id.id)
                courses = courses.parent_id
            batches = self.env['op.batch'].search([('course_id', 'in', lst)])
            return batches.name_get()
        return super(OpBatch, self).name_search(
            name, args, operator=operator, limit=limit)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Batch'),
            'template': '/openeducat_core/static/xls/op_batch.xls'
        }]

    def allocate_students(self):
        new_students = self.env['op.student'].search([('batch_id', '=', self.id)])

        for record in self:
            existing_students = record.student_ids.mapped('student_id')  # Get existing student_ids

            # Add students without duplicates
            for student in new_students:
                if student.id not in existing_students:  # Check if the student is already in the One2many field
                    print(student.name, 'student')
                    record.student_ids = [(0, 0, {'student_id': student.id, 'student_name': student.id})]


class StudentList(models.Model):
    _name = 'logic.student.list'

    student_id = fields.Integer(string="ID")
    student_name = fields.Many2one('op.student', string="Name")
    date_of_admission = fields.Date(string="Admission Date")
    admission_fee = fields.Integer(string="Admission Fee")
    course_fee = fields.Integer(string="Course Fee")
    total_paid = fields.Integer(string="Total Paid", compute="_compute_total_paid_amount", store=1)
    batch_id = fields.Many2one('op.batch', ondelete="cascade")

    @api.depends('course_fee', 'admission_fee')
    def _compute_total_paid_amount(self):
        for rec in self:
            rec.total_paid = rec.course_fee + rec.admission_fee

class InstallmentPayment(models.Model):
    _name = 'payment.installment.type'

    term = fields.Char(string="Term")
    amount_exc_installment = fields.Float(string="Amount(Excluding Tax)")
    tax_amount = fields.Float(string="Tax Amount")
    amount_inc_installment = fields.Float(string="Amount(Including Tax)", compute='_compute_amount_inc_installment', store=1)
    payment_date = fields.Date(string="Payment Date")
    installment_id = fields.Many2one('op.batch', string="Installment")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id.id)

    @api.depends('amount_exc_installment','tax_amount')
    def _compute_amount_inc_installment(self):
        for i in self:
            if i.tax_amount != 0:
                i.amount_inc_installment = i.amount_exc_installment + i.tax_amount
