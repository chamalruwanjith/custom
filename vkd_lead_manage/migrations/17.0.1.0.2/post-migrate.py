def migrate(cr, version):
    # from_time/to_time are now computed from shift_id + shift_date + company timezone.
    # Trigger recompute for all existing lead.allocate records that have a shift_id set.
    cr.execute("""
        UPDATE lead_allocate SET write_date = NOW()
        WHERE shift_id IS NOT NULL
    """)
