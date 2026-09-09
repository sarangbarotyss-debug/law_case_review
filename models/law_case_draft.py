# -*- coding: utf-8 -*-
from odoo import models, fields, api
from ..services.case_draft_service import CaseDraftService


class LawCaseDraft(models.Model):
    _name = 'law.case.draft'
    _description = 'AI-Generated Case Draft Document'
    _order = 'create_date desc'

    case_id = fields.Many2one(
        'law.case',
        string='Case',
        required=True,
        ondelete='cascade',
        index=True,
    )
    draft_type = fields.Selection([
        ('legal_notice', 'Legal Notice'),
        ('reply_letter', 'Reply Letter'),
    ], string='Document Type', required=True)

    instructions = fields.Text(
        string='Instructions',
        help="Optional free-text instructions given by the lawyer at generation time.",
    )

    content = fields.Html(string='Draft Content')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('reviewed', 'Reviewed'),
        ('finalized', 'Finalized'),
    ], string='Status', default='draft', required=True)

    generated_document_count = fields.Integer(
        string='Document Count at Generation',
        help="Number of case documents that existed when this draft was generated.",
    )
    is_stale = fields.Boolean(
        string='Stale',
        compute='_compute_is_stale',
    )
    new_document_count = fields.Integer(
        string='New Documents Since Generation',
        compute='_compute_is_stale',
    )

    @api.depends('case_id.document_ids', 'generated_document_count')
    def _compute_is_stale(self):
        for rec in self:
            current_count = len(rec.case_id.document_ids) if rec.case_id else 0
            diff = current_count - (rec.generated_document_count or 0)
            rec.new_document_count = diff if diff > 0 else 0
            rec.is_stale = diff > 0

    def action_generate_content_job(self):
        """Runs in the background via queue_job. Builds the prompt from
        all of the case's OCR'd documents, calls the AI, and saves the result.
        """
        self.ensure_one()
        try:
            content = CaseDraftService.generate(self.env, self.id)
            self.write({'content': content})
        except Exception as e:
            self.env['ir.logging'].create({
                'name': 'law_case_draft',
                'type': 'server',
                'level': 'ERROR',
                'dbname': self.env.cr.dbname,
                'message': f"Draft generation failed for draft id {self.id}: {e}",
                'path': 'law_case_draft',
                'func': 'action_generate_content_job',
                'line': '0',
            })
            self.env.cr.commit()
            raise

    def action_mark_reviewed(self):
        self.ensure_one()
        self.write({'state': 'reviewed'})

    def action_mark_finalized(self):
        self.ensure_one()
        self.write({'state': 'finalized'})