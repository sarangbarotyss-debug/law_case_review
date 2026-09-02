# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

SUPPORTED_DIMENSIONS = [768, 1024, 1536, 3072]


class LawEmbeddingModelOption(models.Model):
    _name = 'law.embedding.model.option'
    _description = 'Available Embedding Model Option for Law Case Review'
    _order = 'provider, name'

    name = fields.Char(string='Display Name', required=True)
    provider = fields.Selection([
        ('mistral', 'Mistral'),
        ('google', 'Google'),
    ], string='Provider', required=True)
    model_string = fields.Char(string='Model String', required=True)
    dimension = fields.Integer(
        string='Vector Dimension',
        required=True,
        help="The length of the embedding vector this model produces, e.g. 1024. "
             "Used to detect incompatible embeddings if the active model changes.",
    )
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('dimension')
    def _check_dimension_supported(self):
        for rec in self:
            if rec.dimension not in SUPPORTED_DIMENSIONS:
                raise ValidationError(
                    "Vector Dimension %d is not supported. Supported dimensions are: %s.\n"
                    "Adding a new dimension requires a schema update - contact your developer."
                    % (rec.dimension, ', '.join(str(d) for d in SUPPORTED_DIMENSIONS))
                )