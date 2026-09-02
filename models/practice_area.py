# -*- coding: utf-8 -*-
from odoo import models, fields


class LawPracticeArea(models.Model):
    _name = 'law.practice.area'
    _description = 'Law Practice Area'
    _order = 'name'

    name = fields.Char(string='Practice Area', required=True)
    active = fields.Boolean(default=True)