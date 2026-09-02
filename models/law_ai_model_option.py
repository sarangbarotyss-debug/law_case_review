# -*- coding: utf-8 -*-
from odoo import models, fields


class LawAIModelOption(models.Model):
    _name = 'law.ai.model.option'
    _description = 'Available AI Model Option for Law Case Review'
    _order = 'provider, name'

    name = fields.Char(string='Display Name', required=True)
    provider = fields.Selection([
        ('openai', 'OpenAI'),
        ('gemini', 'Gemini'),
        ('anthropic', 'Anthropic'),
        ('openrouter', 'OpenRouter'),
        ('groq', 'Groq'),
    ], string='Provider', required=True)
    model_string = fields.Char(string='Model String', required=True)
    active = fields.Boolean(string='Active', default=True)