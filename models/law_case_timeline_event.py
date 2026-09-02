# -*- coding: utf-8 -*-

from odoo import api, models, fields


class LawCaseTimelineEvent(models.Model):
    _name = 'law.case.timeline.event'
    _description = 'Case Timeline Event'
    _order = 'event_date asc, id asc'

    case_id = fields.Many2one('law.case', string='Case', required=True, ondelete='cascade', index=True)
    document_id = fields.Many2one('law.case.document', string='Source Document', ondelete='set null')

    event_date = fields.Date(string='Event Date')
    event_date_text = fields.Char(string='Date (as in document)')

    title = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    event_type = fields.Selection([
        ('filing', 'Filing'),
        ('hearing', 'Hearing'),
        ('notice', 'Notice'),
        ('agreement', 'Agreement'),
        ('incident', 'Incident'),
        ('correspondence', 'Correspondence'),
        ('other', 'Other'),
    ], string='Event Type', default='other')

    source_snippet = fields.Text(string='Source Snippet')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True)

    manually_edited = fields.Boolean(string='Manually Edited', default=False)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def write(self, vals):
        # if a lawyer edits date/title/description on a draft, flag it as human-corrected
        tracked_fields = {'event_date', 'event_date_text', 'title', 'description'}
        if tracked_fields.intersection(vals.keys()) and 'manually_edited' not in vals:
            for rec in self:
                if rec.state == 'draft':
                    vals_copy = dict(vals)
                    vals_copy['manually_edited'] = True
                    super(LawCaseTimelineEvent, rec).write(vals_copy)
                else:
                    super(LawCaseTimelineEvent, rec).write(vals)
            return True
        return super().write(vals)

    def action_preview_document(self):
        self.ensure_one()
        if not self.document_id or not self.document_id.file:
            return
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'law.case.document'),
            ('res_id', '=', self.document_id.id),
            ('res_field', '=', 'file'),
        ], limit=1)
        if not attachment:
            return
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=false' % attachment.id,
            'target': 'new',
        }