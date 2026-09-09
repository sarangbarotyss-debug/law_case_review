from odoo import models, fields, api


class LawCaseDraftWizard(models.TransientModel):
    _name = 'law.case.draft.wizard'
    _description = 'Generate AI Case Draft Wizard'

    case_id = fields.Many2one(
        'law.case',
        string='Case',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    draft_type = fields.Selection([
        ('legal_notice', 'Legal Notice'),
        ('reply_letter', 'Reply Letter'),
    ], string='Document Type', required=True)

    instructions = fields.Text(
        string='Additional Instructions',
        help="Optional — e.g. 'focus on breach of contract, keep it under 2 pages'.",
    )

    def action_generate_draft(self):
        self.ensure_one()
        # Creates the draft record immediately in 'draft' state,
        # then queues the actual AI generation as a background job.
        draft = self.env['law.case.draft'].create({
            'case_id': self.case_id.id,
            'draft_type': self.draft_type,
            'instructions': self.instructions,
            'generated_document_count': len(self.case_id.document_ids),
        })
        draft.with_delay().action_generate_content_job()
        return {'type': 'ir.actions.act_window_close'}