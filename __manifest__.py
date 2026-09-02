# -*- coding: utf-8 -*-
{
    'name': "law_case_review",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Yotta Software Solutions",
    'website': "https://www.yourcompany.com",

    
    'category': 'Uncategorized',
    'version': '19.0.0.0.0',

    'post_init_hook': 'post_init_hook',

    
    'depends': ['base', 'base_setup', 'queue_job', 'dms'],
    'external_dependencies': {
        'python': ['requests', 'markdown'],
    },

   
    'data': [
        'security/law_case_security.xml',
        'security/law_case_record_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/queue_job_data.xml',
        'data/dms_data.xml',
        'wizards/embedding_model_change_wizard_views.xml',
        'views/law_case_views.xml',
        'views/law_case_document_views.xml',
        'views/res_config_settings_views.xml',
        'views/law_ai_model_option_views.xml',
        'views/law_client_request_views.xml',
        'views/law_embedding_model_option_views.xml',
        'views/law_playbook_source_views.xml',
        'wizards/client_request_upload_wizard_views.xml',
        'views/practice_area_views.xml',
        'views/menus.xml',
    ],

    'assets':{
        'web.assets_backend':[
            'law_case_review/static/src/js/client_request_list.js',
            'law_case_review/static/src/xml/client_request_list.xml',
            'law_case_review/static/src/js/document_preview_panel.js',
            'law_case_review/static/src/xml/document_preview_panel.xml',
            'law_case_review/static/src/js/form_controller_preview.js',
            'law_case_review/static/src/xml/form_controller_preview.xml',
            'law_case_review/static/src/css/document_preview_panel.css',
            'law_case_review/static/src/js/case_qa_panel.js',
            'law_case_review/static/src/js/case_qa_form_controller.js',
            'law_case_review/static/src/xml/case_qa_templates.xml',
            'law_case_review/static/src/css/case_qa_panel.scss',
            'law_case_review/static/src/js/embedding_reembed_progress_widget.js',
            'law_case_review/static/src/xml/embedding_reembed_progress_widget.xml',
            'law_case_review/static/src/js/client_request_progress_widget.js',
            'law_case_review/static/src/xml/client_request_progress_widget.xml',
            'law_case_review/static/src/js/async_field_watcher.js',
            'law_case_review/static/src/xml/async_field_watcher.xml',
        ],
    },
}

