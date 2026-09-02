# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LawEmbeddingModelChangeWizard(models.TransientModel):
    _name = 'law.embedding.model.change.wizard'
    _description = 'Confirm Embedding Model Change and Re-embed'

    old_model_id = fields.Many2one('law.embedding.model.option', string='Current Model', readonly=True)
    new_model_id = fields.Many2one('law.embedding.model.option', string='New Model', readonly=True)
    stage = fields.Selection([
        ('confirm', 'Confirm'),
        ('progress', 'In Progress'),
    ], default='confirm')
    done_count = fields.Integer(default=0)
    total_count = fields.Integer(default=0)
    error_count = fields.Integer(default=0)

    def action_cancel(self):
        # Old model was already restored server-side when this wizard was
        # created (see res_config_settings.execute()). Nothing else to do.
        return {'type': 'ir.actions.act_window_close'}

    def action_start_reembed(self):
        self.ensure_one()
        from ..models.reembed_service import count_missing_for_model

        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('law_case_review.embedding_model_id', str(self.new_model_id.id))

        total = count_missing_for_model(self.env, self.new_model_id)
        self.write({
            'stage': 'progress',
            'total_count': total,
            'done_count': 0,
            'error_count': 0,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'law.embedding.model.change.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_process_batch(self, batch_size=5):
        """
        Called repeatedly by the JS widget until all records are done.
        Processes one batch, updates and returns running totals.
        """
        self.ensure_one()
        from ..models.reembed_service import process_batch_for_model

        processed, errors = process_batch_for_model(self.env, self.new_model_id, batch_size=batch_size)
        self.done_count += processed
        self.error_count += errors
        self.env.cr.commit()

        return {
            'total_count': self.total_count,
            'done_count': self.done_count,
            'error_count': self.error_count,
            'is_complete': self.done_count >= self.total_count,
        }