# -*- coding: utf-8 -*-
from odoo import models, fields


class LawAICache(models.Model):
    _name = 'law.ai.cache'
    _description = 'AI Response Cache for Law Case Review'

    cache_key = fields.Char(string='Cache Key', required=True, index=True)
    cache_type = fields.Selection([
        ('embedding', 'Embedding'),
    ], string='Cache Type', required=True, default='embedding')
    value = fields.Text(string='Cached Value', required=True)