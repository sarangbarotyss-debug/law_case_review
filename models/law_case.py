# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LawCase(models.Model):
    _name = 'law.case'
    _description = 'Law Case'

    name = fields.Char(string='Case Reference', required=True, readonly=True, copy=False, default='New')
    client_id = fields.Many2one('res.partner', string='Client', required=True)
    lawyer_id = fields.Many2one('res.users', string='Assigned Lawyer', default=lambda self: self.env.user)
    document_ids = fields.One2many('law.case.document', 'case_id', string='Documents')
    match_ids = fields.One2many('law.case.playbook.match', 'case_id', string='Playbook Matches')
    qa_log_ids = fields.One2many('law.case.qa.log', 'case_id', string='Q&A History')
    party_ids = fields.One2many('law.case.party', 'case_id', string='Case Parties')
    hearing_ids = fields.One2many('law.case.hearing', 'case_id', string='Hearings')
    practice_area_id = fields.Many2one('law.practice.area', string='Practice Area')
    outcome = fields.Selection([
        ('open', 'Open'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('settled', 'Settled'),
    ], string='Outcome', default='open', required=True)
    closure_date = fields.Date(string='Closure Date')
    matter_type = fields.Char(string='Type of Matter')
    description = fields.Text(string='Case Description', required=True)
    playbook_source_ids = fields.Many2many(
        'law.playbook.source',
        string='Relevant Playbook Sources',
        help="Select which reference documents (e.g. Constitution, specific statutes) "
             "this case should be compared against.",
        required=True
    )
    playbook_match_running = fields.Boolean(string='Playbook Comparison Running', default=False, readonly=True)
    dms_directory_id = fields.Many2one('dms.directory', string='Document Folder', readonly=True, copy=False)
    timeline_event_ids = fields.One2many('law.case.timeline.event', 'case_id', string='Timeline Events')
    is_case_manager = fields.Boolean(compute='_compute_is_case_manager')
    visible_timeline_event_ids = fields.One2many(
        'law.case.timeline.event', 'case_id', string='Timeline Events',
        domain=[('state', '!=', 'rejected')]
    )
    draft_timeline_event_label = fields.Char(compute='_compute_draft_timeline_event_count')
    case_brief_html = fields.Html(string='Case Brief', copy=False)
    case_brief_generated_at = fields.Datetime(string='Brief Generated On', readonly=True, copy=False)
    case_brief_generating = fields.Boolean(string='Case Brief Generating', default=False, copy=False)
    case_brief_stale_count = fields.Integer(compute='_compute_case_brief_stale_count')
    timeline_extraction_running = fields.Boolean(
        string='Timeline Extraction Running',
        compute='_compute_timeline_extraction_running',
    )
    qa_last_content_update = fields.Datetime(string='Last Content Update for Q&A', copy=False)
    draft_ids = fields.One2many('law.case.draft', 'case_id', string='Drafts')

    def _touch_qa_content_version(self):
        self.write({'qa_last_content_update': fields.Datetime.now()})

    def write(self, vals):
        result = super().write(vals)
        if 'playbook_source_ids' in vals:
            self._touch_qa_content_version()
        return result

    def _compute_is_case_manager(self):
        is_manager = self.env.user.has_group('law_case_review.group_law_case_manager')
        for rec in self:
            rec.is_case_manager = is_manager

    def action_find_playbook_matches(self):
        self.ensure_one()
        self.playbook_match_running = True
        self.with_delay().action_process_playbook_comparison(self.env.user.id)

    def action_process_playbook_comparison(self, user_id):
        self.ensure_one()
        
        partner = self.env['res.users'].browse(user_id).partner_id
        try:
            from ..services.case_playbook_comparison_service import run_case_playbook_comparison
            run_case_playbook_comparison(self.env, self)
            self.env['bus.bus']._sendone(partner, 'simple_notification', {
                'type': 'success',
                'title': 'Playbook Comparison Complete',
                'message': f'Playbook matches for {self.name} are ready to view.',
            })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'law_case_review.law_case',
                'type': 'server',
                'level': 'ERROR',
                'message': f'Playbook comparison failed for case {self.id}: {e}',
                'path': 'law_case_review.law_case',
                'func': 'action_process_playbook_comparison',
                'line': '0',
            })
            self.env['bus.bus']._sendone(partner, 'simple_notification', {
                'type': 'danger',
                'title': 'Playbook Comparison Failed',
                'message': 'Something went wrong while comparing this case against the playbook. Please try again or contact support.',
            })
        finally:
            self.playbook_match_running = False
            self.env.cr.commit()

    def action_ask_case_question(self, question):
        self.ensure_one()
        from ..services.case_qa_service import CaseQAService
        return CaseQAService.ask(self.env, self.id, question)

    def action_clear_case_qa(self):
        self.ensure_one()
        self.qa_log_ids.write({'hidden_from_chat': True})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('law.case') or 'New'
        records = super().create(vals_list)
        storage = self.env.ref('law_case_review.storage_law_cases', raise_if_not_found=False)
        access_group = self.env.ref('law_case_review.dms_access_group_law_cases', raise_if_not_found=False)
        for case in records:
            if storage:
                directory = self.env['dms.directory'].create({
                    'name': case.name.replace('/', '-'),
                    'storage_id': storage.id,
                    'is_root_directory': True,
                    'group_ids': [(4, access_group.id)] if access_group else False,
                })
                case.dms_directory_id = directory.id
        return records

    def action_open_dms_directory(self):
        self.ensure_one()
        if not self.dms_directory_id:
            raise UserError(_("No document folder linked to this case yet."))
        action = self.env["ir.actions.act_window"]._for_xml_id("dms.action_dms_file")
        action['context'] = dict(
            self.env.context,
            default_directory_id=self.dms_directory_id.id,
            searchpanel_default_directory_id=self.dms_directory_id.id,
        )
        return action

    def action_extract_timeline_all(self):
        self.ensure_one()
        docs_to_process = self.document_ids.filtered(lambda d: not d.timeline_extracted and d.ocr_text)
        if not docs_to_process:
            raise UserError('No unprocessed documents with extracted text found.')
        docs_to_process.action_extract_timeline_async()

    def _compute_draft_timeline_event_count(self):
        for rec in self:
            count = len(rec.timeline_event_ids.filtered(lambda e: e.state == 'draft'))
            rec.draft_timeline_event_label = f'{count} draft(s) awaiting review' if count else False

    def action_generate_case_brief(self):
        self.ensure_one()
        self.case_brief_generating = True
        self.with_delay(description='Generate case brief for %s' % self.name).action_generate_case_brief_job()

    def action_generate_case_brief_job(self):
        self.ensure_one()
        try:
            from ..services.case_brief_service import generate_case_brief
            brief_html = generate_case_brief(self.env, self)
            self.write({
                'case_brief_html': brief_html,
                'case_brief_generated_at': fields.Datetime.now(),
            })
        finally:
            self.case_brief_generating = False

    def _compute_case_brief_stale_count(self):
        for rec in self:
            if not rec.case_brief_generated_at:
                rec.case_brief_stale_count = 0
                continue
            rec.case_brief_stale_count = len(rec.document_ids.filtered(
                lambda d: d.write_date and d.write_date > rec.case_brief_generated_at
            ))

    def _compute_timeline_extraction_running(self):
        for rec in self:
            rec.timeline_extraction_running = any(rec.document_ids.mapped('timeline_extraction_queued'))