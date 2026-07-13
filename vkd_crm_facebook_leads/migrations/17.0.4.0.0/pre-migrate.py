def migrate(cr, version):
    # project_id on crm.lead and crm.facebook.form changes its comodel from
    # apartment.details to crm.lead.project. The stored integers are apartment.details
    # ids and are meaningless against the new table, so snapshot the links by NAME and
    # clear the columns — otherwise creating the new foreign key fails on existing rows.
    if not version:
        return

    cr.execute("""
        CREATE TABLE IF NOT EXISTS vkd_lead_project_migration (
            res_model varchar,
            res_id integer,
            project_name varchar
        )
    """)

    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'apartment_details'")
    if not cr.fetchone():
        return

    cr.execute("""
        INSERT INTO vkd_lead_project_migration (res_model, res_id, project_name)
        SELECT 'crm.lead', l.id, a.apartment_name
        FROM crm_lead l
        JOIN apartment_details a ON a.id = l.project_id
        WHERE l.project_id IS NOT NULL
    """)
    cr.execute("""
        INSERT INTO vkd_lead_project_migration (res_model, res_id, project_name)
        SELECT 'crm.facebook.form', f.id, a.apartment_name
        FROM crm_facebook_form f
        JOIN apartment_details a ON a.id = f.project_id
        WHERE f.project_id IS NOT NULL
    """)

    cr.execute("UPDATE crm_lead SET project_id = NULL WHERE project_id IS NOT NULL")
    cr.execute("UPDATE crm_facebook_form SET project_id = NULL WHERE project_id IS NOT NULL")