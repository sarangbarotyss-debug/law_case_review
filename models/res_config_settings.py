# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    law_ai_provider = fields.Selection([
        ('openai', 'OpenAI'),
        ('gemini', 'Gemini'),
        ('anthropic', 'Anthropic'),
        ('openrouter', 'OpenRouter'),
        ('groq', 'Groq'),
    ], string='AI Provider', config_parameter='law_case_review.ai_provider', default='openai')

    law_ai_model_id = fields.Many2one(
        'law.ai.model.option',
        string='AI Model',
        config_parameter='law_case_review.ai_model_id',
        domain="[('provider', '=', law_ai_provider), ('active', '=', True)]",
    )

    law_ai_api_key = fields.Char(string='API Key', config_parameter='law_case_review.ai_api_key')

    law_embedding_provider = fields.Selection([
        ('mistral', 'Mistral'),
        ('google', 'Google'),
    ], string='Embedding Provider', config_parameter='law_case_review.embedding_provider', default='mistral')

    law_embedding_model_id = fields.Many2one(
        'law.embedding.model.option',
        string='Embedding Model',
        config_parameter='law_case_review.embedding_model_id',
        domain="[('provider', '=', law_embedding_provider), ('active', '=', True)]",
    )

    law_mistral_api_key = fields.Char(string='Mistral API Key', config_parameter='law_case_review.mistral_api_key')

    law_google_api_key = fields.Char(string='Google API Key', config_parameter='law_case_review.google_api_key')

    def execute(self):

        if self.law_embedding_provider and not self.law_embedding_model_id:
            raise ValidationError(
                "Please select an Embedding Model for the chosen Provider (%s) before saving."
                % dict(self._fields['law_embedding_provider'].selection).get(self.law_embedding_provider)
            )
        if self.law_embedding_model_id and self.law_embedding_model_id.provider != self.law_embedding_provider:
            raise ValidationError(
                "The selected Embedding Model (%s) does not belong to the selected Provider (%s). "
                "Please re-select a matching model."
                % (self.law_embedding_model_id.name, dict(self._fields['law_embedding_provider'].selection).get(self.law_embedding_provider))
            )

        if self.law_ai_provider and not self.law_ai_model_id:
            raise ValidationError(
                "Please select an AI Model for the chosen Provider (%s) before saving."
                % dict(self._fields['law_ai_provider'].selection).get(self.law_ai_provider)
            )
        if self.law_ai_model_id and self.law_ai_model_id.provider != self.law_ai_provider:
            raise ValidationError(
                "The selected AI Model (%s) does not belong to the selected Provider (%s). "
                "Please re-select a matching model."
                % (self.law_ai_model_id.name, dict(self._fields['law_ai_provider'].selection).get(self.law_ai_provider))
            )
        
        ICP = self.env['ir.config_parameter'].sudo()
        old_embedding_model_id = ICP.get_param('law_case_review.embedding_model_id')

        result = super().execute()

        new_embedding_model_id = str(self.law_embedding_model_id.id) if self.law_embedding_model_id else False

        if old_embedding_model_id and new_embedding_model_id and old_embedding_model_id != new_embedding_model_id:
            ICP.set_param('law_case_review.embedding_model_id', old_embedding_model_id)

            wizard = self.env['law.embedding.model.change.wizard'].create({
                'old_model_id': int(old_embedding_model_id),
                'new_model_id': int(new_embedding_model_id),
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'law.embedding.model.change.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }

        return result

    @api.onchange('law_embedding_provider')
    def _onchange_law_embedding_provider(self):
        if self.law_embedding_model_id and self.law_embedding_model_id.provider != self.law_embedding_provider:
            self.law_embedding_model_id = False

    @api.onchange('law_ai_provider')
    def _onchange_law_ai_provider(self):
        if self.law_ai_model_id and self.law_ai_model_id.provider != self.law_ai_provider:
            self.law_ai_model_id = False