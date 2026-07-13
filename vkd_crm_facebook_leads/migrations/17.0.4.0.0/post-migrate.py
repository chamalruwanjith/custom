def migrate(cr, version):
    # Companion to pre-migrate: seed crm.lead.project from the existing apartment
    # names, then restore the crm.lead / crm.facebook.form links by matching on name.
    if not version:
        return

    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_lead_project'")
    if not cr.fetchone():
        return

    # Seed the new project list from apartment.details so the dropdown starts populated.
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'apartment_details'")
    if cr.fetchone():
        cr.execute("""
            INSERT INTO crm_lead_project (name, active, create_uid, write_uid, create_date, write_date)
            SELECT s.name, true, 1, 1, now(), now()
            FROM (
                SELECT DISTINCT ON (lower(apartment_name)) apartment_name AS name
                FROM apartment_details
                WHERE apartment_name IS NOT NULL AND apartment_name != ''
                ORDER BY lower(apartment_name), id
            ) s
            WHERE NOT EXISTS (
                SELECT 1 FROM crm_lead_project p WHERE lower(p.name) = lower(s.name)
            )
        """)

    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'vkd_lead_project_migration'")
    if not cr.fetchone():
        return

    # Cover any snapshotted name that no longer exists in apartment.details.
    cr.execute("""
        INSERT INTO crm_lead_project (name, active, create_uid, write_uid, create_date, write_date)
        SELECT s.name, true, 1, 1, now(), now()
        FROM (
            SELECT DISTINCT ON (lower(project_name)) project_name AS name
            FROM vkd_lead_project_migration
            WHERE project_name IS NOT NULL AND project_name != ''
            ORDER BY lower(project_name)
        ) s
        WHERE NOT EXISTS (
            SELECT 1 FROM crm_lead_project p WHERE lower(p.name) = lower(s.name)
        )
    """)

    cr.execute("""
        UPDATE crm_lead l
        SET project_id = p.id
        FROM vkd_lead_project_migration m, crm_lead_project p
        WHERE m.res_model = 'crm.lead'
          AND l.id = m.res_id
          AND lower(p.name) = lower(m.project_name)
    """)
    cr.execute("""
        UPDATE crm_facebook_form f
        SET project_id = p.id
        FROM vkd_lead_project_migration m, crm_lead_project p
        WHERE m.res_model = 'crm.facebook.form'
          AND f.id = m.res_id
          AND lower(p.name) = lower(m.project_name)
    """)

    cr.execute("DROP TABLE vkd_lead_project_migration")