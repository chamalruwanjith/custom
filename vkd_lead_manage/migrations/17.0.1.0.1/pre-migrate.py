def migrate(cr, version):
    # shift_type (Selection, tracking=True) was removed from lead.allocate and replaced
    # by shift_id (Many2one to lead.shift). Odoo's mail module overrides ir.model.fields
    # unlink to call _mail_track_get_field_sequence(), which fails if the Python field is
    # already gone. Delete via raw SQL to bypass the ORM override before _process_end runs.
    cr.execute("""
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'lead.allocate' AND name = 'shift_type'
        )
    """)
    cr.execute("""
        DELETE FROM mail_tracking_value
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'lead.allocate' AND name = 'shift_type'
        )
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'lead.allocate' AND name = 'shift_type'
    """)
