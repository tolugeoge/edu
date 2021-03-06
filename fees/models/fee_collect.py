# -*- coding: utf-8 -*-

from openerp import api, fields, models


class FeeCollectMaster(models.Model):

    _inherit = ['account.invoice']

    is_fee_invoice = fields.Boolean()


class FeeCollect(models.Model):
    _name = 'edu.fee.collect'
    _rec_name = 'student_id'


    # @api.onchange('template_id')
    # def _onchange_template_id(self):
    #     # total = 0.0
    #     # for product in self.fee_line_ids:
    #     #     total += product.list_price
    #     self.total = self.template_id.total

    @api.multi
    @api.depends('template_id')
    def _compute_total(self):
        for record in self:
            record.total = sum(line.list_price for line in record.fee_line_ids)

    # name = fields.Char()
    student_id = fields.Many2one('op.student', 'Student', required=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True)
    course_id = fields.Many2one(related='batch_id.course_id', store=True, readonly=True)
    template_id = fields.Many2one('edu.fee.template', 'Fee Template', required=True)
    fee_line_ids = fields.Many2many(#'edu.fee.template', 'edu_fee_line_rel', 'fee_collect_id', 'fee_id',
        related='template_id.fee_line_ids', string='Fee Lines', store=True)
    total = fields.Monetary('Total', compute=_compute_total, store=True, readonly=True)
    # total = fields.Monetary('Total', readonly=True)
    # total = fields.Monetary('Total', related='template_id.total', readonly=True)
    date = fields.Date(required=True, default=fields.Date.today())
    currency_id = fields.Many2one('res.currency', string='Currency')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    state = fields.Selection([('draft', 'Invoice'), ('validated', 'Validated')], default='draft')


    @api.multi
    def confirm_fee_validate(self):
        for record in self:
            record.invoice_id.signal_workflow('invoice_open')
            record.write({'state': 'validated'})


    @api.model
    def create(self, vals):
        AccountInvoice = self.env['account.invoice']
        AccountInvoiceLine= self.env['account.invoice.line']
        fee_collect = super(FeeCollect, self).create(vals)

        invoice = AccountInvoice.create({
            'partner_id': fee_collect.student_id.partner_id.id,
            'account_id': fee_collect.student_id.partner_id.property_account_receivable_id.id,
            'type': 'out_invoice',
            'origin': fee_collect.id,
            'is_fee_invoice': True,
            # 'currency_id': self.user.company_id.currency_id.id,
            })
        fee_collect.invoice_id = invoice.id

        invoice_type = invoice.type
        fpos = invoice.fiscal_position_id
        company = invoice.company_id

        for product in fee_collect.fee_line_ids:
            account = AccountInvoiceLine.get_invoice_line_account(invoice_type, product, fpos, company)
            invoice_line_vals = {
                'name': product.name,
                'product_id': product.id,
                'price_unit': product.list_price,
                'account_id': account.id,
                'invoice_id': invoice.id
                }
            AccountInvoiceLine.create(invoice_line_vals)
        return fee_collect

