import base64
import io
import pytz
from datetime import datetime
from collections import defaultdict

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter


class CRMLeadReport(models.TransientModel):
    _name = 'crm.lead.report'
    _description = 'Generate Excel Report for Leads'

    report_by = fields.Selection(
        [('date', 'Date'), ('range', 'Date Range')],
        string="Report By", required=True, default='date'
    )
    start_date = fields.Date(string="Date", required=True)
    end_date = fields.Date(string="End Date")
    shift_id = fields.Many2one('lead.shift', string="Shift")
    company_ids = fields.Many2many('res.company', string="Companies")

    def action_generate_report(self):
        colombo_tz = pytz.timezone('Asia/Colombo')

        if not self.end_date:
            self.end_date = self.start_date
        if self.start_date > self.end_date:
            raise UserError(_("Start Date cannot be greater than End Date."))

        domain = [
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date),
        ]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        leads = self.env['crm.lead'].search(domain, order='create_date desc')
        if not leads:
            raise UserError(_("No leads found for the selected period."))

        leads = self._filter_by_shift(leads, colombo_tz)
        if not leads:
            raise UserError(_("No leads found for the selected period and shift."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Split Lands vs Apartments by the ad set category (D01/D02 = Apartment,
        # everything else — including leads with no ad set — = Lands).
        apartment_leads = leads.filtered(lambda l: l.adset_category == 'apartment')
        lands_leads = leads - apartment_leads

        self._generate_leads_sheet(workbook, leads, colombo_tz)
        self._generate_summary_sheet(workbook, leads)
        self._generate_attend_sheet(workbook, lands_leads, colombo_tz, 'Lands')
        self._generate_attend_sheet(workbook, apartment_leads, colombo_tz, 'Apartments')
        self._generate_project_sheet(workbook, lands_leads, colombo_tz, 'Lands')
        self._generate_project_sheet(workbook, apartment_leads, colombo_tz, 'Apartments')
        self._generate_agent_count_sheet(workbook, leads, colombo_tz)

        workbook.close()
        output.seek(0)

        encoded_data = base64.b64encode(output.getvalue()).decode('utf-8')
        attachment_id = self.env['ir.attachment'].create({
            'name': f"{self.start_date} - {_('Leads Report')}.xlsx",
            'datas': encoded_data,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "download",
        }

    def _filter_by_shift(self, leads, colombo_tz):
        if not self.shift_id:
            return leads
        from_h = self.shift_id.from_hour
        to_h = self.shift_id.to_hour
        next_day = self.shift_id.next_day

        def _in_shift(lead):
            if not lead.create_date:
                return False
            local_dt = pytz.utc.localize(lead.create_date).astimezone(colombo_tz)
            t = local_dt.hour + local_dt.minute / 60.0
            if next_day:
                return t >= from_h or t < to_h
            return from_h <= t < to_h

        return leads.filtered(_in_shift)

    def _period_label(self):
        sd, ed = self.start_date, self.end_date
        return sd.strftime('%m/%d/%Y') if sd == ed else \
            f"{sd.strftime('%m/%d/%Y')} - {ed.strftime('%m/%d/%Y')}"

    def _shift_label(self):
        return self.shift_id.name if self.shift_id else 'All Leads'

    @staticmethod
    def _convert_to_local_time(datetime_field, timezone):
        if datetime_field:
            return pytz.utc.localize(datetime_field).astimezone(timezone).strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'

    def _generate_leads_sheet(self, workbook, leads, colombo_tz):
        worksheet = workbook.add_worksheet("Leads Report")

        header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#F0F0F0', 'border': 1, 'text_wrap': True})
        data_fmt   = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        num_fmt    = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

        headers = [
            'Created Date', 'Created Time', 'Campaign',
            'Full Name', 'Email', 'Contact Number', 'WhatsApp Number',
            'Agent', 'Digital Team', 'Attended Time', 'Response Time (min)', 'Shift',
        ]
        col_widths = [14, 12, 20, 25, 28, 18, 18, 20, 16, 20, 14, 16]
        for col, (w, h) in enumerate(zip(col_widths, headers)):
            worksheet.set_column(col, col, w)
            worksheet.write(0, col, h, header_fmt)
        worksheet.set_row(0, 30)

        def _local(dt):
            if not dt:
                return None, None
            local = pytz.utc.localize(dt).astimezone(colombo_tz)
            return local.strftime('%m/%d/%Y'), local.strftime('%H:%M:%S')

        for row, lead in enumerate(leads, start=1):
            c_date, c_time = _local(lead.create_date)
            a_date, a_time = _local(lead.attend_time)
            attended_str   = f"{a_date} {a_time}" if a_date else ''
            rt             = round(lead.response_time, 2) if lead.response_time else ''
            shift          = lead.lead_allocate_id.shift_id.name if lead.lead_allocate_id and lead.lead_allocate_id.shift_id else ''

            worksheet.write(row, 0,  c_date or '',                          data_fmt)
            worksheet.write(row, 1,  c_time or '',                          data_fmt)
            worksheet.write(row, 2,  lead.campaign_id.name or '',           data_fmt)
            worksheet.write(row, 3,  lead.full_name or '',                  data_fmt)
            worksheet.write(row, 4,  lead.email_from or '',              data_fmt)
            worksheet.write(row, 5,  lead.phone or '',             data_fmt)
            worksheet.write(row, 6,  lead.whatsapp_number or '',            data_fmt)
            worksheet.write(row, 7,  lead.user_id.name or 'Unassigned',    data_fmt)
            worksheet.write(row, 8,  lead.digital_team_id.name or '',       data_fmt)
            worksheet.write(row, 9,  attended_str,                          data_fmt)
            worksheet.write(row, 10, rt,                                    num_fmt)
            worksheet.write(row, 11, shift,                                 data_fmt)

    # ── Sheet 2: Attendance summary (legacy) ────────────────────────────────

    def _generate_summary_sheet(self, workbook, leads):
        worksheet = workbook.add_worksheet("Summary Report")

        header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FFD700', 'border': 1})
        data_fmt = workbook.add_format({'align': 'left', 'border': 1})
        num_fmt = workbook.add_format({'align': 'center', 'border': 1})
        green_fmt = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#C6EFCE'})
        yellow_fmt = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#FFEB9C'})
        red_fmt = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#FFC7CE'})

        for col, h in enumerate(["Attend Time Range", "Count", "Percentage"]):
            worksheet.write(0, col, h, header_fmt)
        worksheet.set_column(0, 2, 30)

        cats = {'0-5': 0, '5-15': 0, 'over_15': 0, 'not_attended': 0}
        for lead in leads:
            if lead.response_time:
                if lead.response_time <= 5:
                    cats['0-5'] += 1
                elif lead.response_time <= 15:
                    cats['5-15'] += 1
                else:
                    cats['over_15'] += 1
            else:
                cats['not_attended'] += 1

        total = len(leads)
        pct_0_5 = (cats['0-5'] / total * 100) if total else 0
        labels = ['0-5 minutes', '5-15 minutes', 'Over 15 minutes', 'Not Attended']
        keys = ['0-5', '5-15', 'over_15', 'not_attended']

        for row, (label, key) in enumerate(zip(labels, keys), start=1):
            count = cats[key]
            pct = (count / total * 100) if total else 0
            worksheet.write(row, 0, label, data_fmt)
            worksheet.write(row, 1, count, num_fmt)
            worksheet.write(row, 2, f"{pct:.2f}%", num_fmt)

        worksheet.write(6, 0, "Overall Percentage (0-5 mins)", header_fmt)
        fmt = green_fmt if pct_0_5 >= 85 else yellow_fmt if pct_0_5 >= 50 else red_fmt
        worksheet.write(6, 1, f"{pct_0_5:.2f}%", fmt)


    def _generate_attend_sheet(self, workbook, leads, colombo_tz, category_label):
        worksheet = workbook.add_worksheet("Attendance Report (%s)" % category_label)

        title_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter'})
        group_hdr_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#BDD7EE', 'border': 1})
        col_hdr_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'bottom', 'bg_color': '#D9E1F2', 'border': 1, 'rotation': 90})
        agent_fmt = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1})
        data_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        total_row_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})
        total_agent_fmt = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})
        green_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#00B050', 'font_color': '#FFFFFF', 'border': 1})
        yellow_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFEB00', 'border': 1})
        red_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FF0000', 'font_color': '#FFFFFF', 'border': 1})

        def _pct_fmt(pct):
            return green_fmt if pct >= 90 else yellow_fmt if pct >= 70 else red_fmt

        ZERO = {'0_5': 0, '5_15': 0, '15p': 0, 'na': 0}
        agent_data = defaultdict(lambda: defaultdict(lambda: dict(ZERO)))
        agent_names = {}
        all_dates = set()

        for lead in leads:
            uid = lead.user_id.id if lead.user_id else 0
            agent_names[uid] = lead.user_id.name if lead.user_id else 'Unassigned'
            local_dt = pytz.utc.localize(lead.create_date).astimezone(colombo_tz)
            date_str = local_dt.strftime('%m/%d/%Y')
            all_dates.add(date_str)
            if lead.attend_time:
                rt = lead.response_time
                if rt <= 5:
                    agent_data[uid][date_str]['0_5'] += 1
                elif rt <= 15:
                    agent_data[uid][date_str]['5_15'] += 1
                else:
                    agent_data[uid][date_str]['15p'] += 1
            else:
                agent_data[uid][date_str]['na'] += 1

        sorted_dates = sorted(all_dates, key=lambda d: datetime.strptime(d, '%m/%d/%Y'))
        sorted_uids = sorted(agent_names.keys(), key=lambda uid: agent_names[uid])

        COLS = 6
        SUB_HDRS = ['0-5 min', '5-15 min', '15 min or above', 'Not Attend', 'Total', '%']
        total_cols = 1 + COLS * (1 + len(sorted_dates))

        title = f"Leads on-time Attending - {self._period_label()} - ({self._shift_label()}) - {category_label}"
        worksheet.merge_range(0, 0, 0, total_cols - 1, title, title_fmt)
        worksheet.set_row(0, 25)

        worksheet.set_row(1, 18)
        worksheet.merge_range(1, 0, 2, 0, '', agent_fmt)
        worksheet.merge_range(1, 1, 1, COLS, 'Total', group_hdr_fmt)
        for i, d in enumerate(sorted_dates):
            c = 1 + COLS * (i + 1)
            worksheet.merge_range(1, c, 1, c + COLS - 1, d, group_hdr_fmt)

        worksheet.set_row(2, 80)
        for g in range(1 + len(sorted_dates)):
            for s, sh in enumerate(SUB_HDRS):
                worksheet.write(2, 1 + g * COLS + s, sh, col_hdr_fmt)

        worksheet.set_column(0, 0, 14)
        for col in range(1, total_cols):
            worksheet.set_column(col, col, 6 if (col - 1) % COLS == 5 else 5)

        def _write_group(row, col_start, b, base_fmt):
            total = b['0_5'] + b['5_15'] + b['15p'] + b['na']
            pct = (b['0_5'] / total * 100) if total > 0 else 0
            worksheet.write(row, col_start,     b['0_5'], base_fmt)
            worksheet.write(row, col_start + 1, b['5_15'], base_fmt)
            worksheet.write(row, col_start + 2, b['15p'],  base_fmt)
            worksheet.write(row, col_start + 3, b['na'],   base_fmt)
            worksheet.write(row, col_start + 4, total,     base_fmt)
            worksheet.write(row, col_start + 5, f"{pct:.0f}%" if total > 0 else '', _pct_fmt(pct) if total > 0 else base_fmt)

        r = 3
        grand = dict(ZERO)
        date_totals = defaultdict(lambda: dict(ZERO))

        for uid in sorted_uids:
            worksheet.write(r, 0, agent_names[uid], agent_fmt)
            overall = dict(ZERO)
            for d in sorted_dates:
                b = agent_data[uid].get(d, ZERO)
                for k in ZERO:
                    overall[k] += b[k]
            _write_group(r, 1, overall, data_fmt)
            for i, d in enumerate(sorted_dates):
                b = agent_data[uid].get(d, ZERO)
                _write_group(r, 1 + COLS * (i + 1), b, data_fmt)
                for k in ZERO:
                    date_totals[d][k] += b[k]
            for k in ZERO:
                grand[k] += overall[k]
            r += 1

        worksheet.write(r, 0, 'TOTAL', total_agent_fmt)
        _write_group(r, 1, grand, total_row_fmt)
        for i, d in enumerate(sorted_dates):
            _write_group(r, 1 + COLS * (i + 1), date_totals[d], total_row_fmt)

    def _generate_project_sheet(self, workbook, leads, colombo_tz, category_label):
        worksheet = workbook.add_worksheet("Project Report (%s)" % category_label)

        title_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter'})
        hdr_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#BDD7EE', 'border': 1, 'text_wrap': True})
        data_fmt = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        num_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        total_label_fmt = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})
        total_num_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})

        # key: (branch, project, type, region, digital_team)
        # value: {date_str: count}
        group_data = defaultdict(lambda: defaultdict(int))
        all_dates = set()

        for lead in leads:
            branch = lead.branch_id.name if lead.branch_id else '(No Branch)'
            project = lead.project_id.name if lead.project_id else '(No Project)'
            ltype = lead.lead_type_id.name if lead.lead_type_id else '(No Type)'
            country = dict(lead._fields['source_region'].selection).get(lead.source_region) or '(No Region)'
            dteam = lead.digital_team_id.name if lead.digital_team_id else '(No Team)'
            key = (branch, project, ltype, country, dteam)

            local_dt = pytz.utc.localize(lead.create_date).astimezone(colombo_tz)
            date_str = local_dt.strftime('%m/%d/%Y')
            all_dates.add(date_str)
            group_data[key][date_str] += 1

        sorted_dates = sorted(all_dates, key=lambda d: datetime.strptime(d, '%m/%d/%Y'))
        sorted_keys = sorted(group_data.keys())

        HEADERS = ['BRANCH', 'PROJECT', 'TYPE', 'REGION', 'DIGITAL TEAM']
        FIXED_COLS = len(HEADERS)
        total_cols = FIXED_COLS + len(sorted_dates) + 1  # +1 for TOTAL column

        title = f"Leads by Project - {self._period_label()} - ({self._shift_label()}) - {category_label}"
        worksheet.merge_range(0, 0, 0, total_cols - 1, title, title_fmt)
        worksheet.set_row(0, 25)

        for col, h in enumerate(HEADERS):
            worksheet.write(1, col, h, hdr_fmt)
        for i, d in enumerate(sorted_dates):
            worksheet.write(1, FIXED_COLS + i, d, hdr_fmt)
        worksheet.write(1, FIXED_COLS + len(sorted_dates), 'TOTAL', hdr_fmt)

        worksheet.set_column(0, 0, 12)  # BRANCH
        worksheet.set_column(1, 1, 28)  # PROJECT
        worksheet.set_column(2, 2, 10)  # TYPE
        worksheet.set_column(3, 3, 16)  # REGION
        worksheet.set_column(4, 4, 14)  # DIGITAL TEAM
        for col in range(FIXED_COLS, total_cols):
            worksheet.set_column(col, col, 10)

        date_totals = defaultdict(int)
        grand_total = 0
        r = 2

        for key in sorted_keys:
            branch, project, ltype, country, dteam = key
            row_total = sum(group_data[key].values())
            worksheet.write(r, 0, branch, data_fmt)
            worksheet.write(r, 1, project, data_fmt)
            worksheet.write(r, 2, ltype, data_fmt)
            worksheet.write(r, 3, country, data_fmt)
            worksheet.write(r, 4, dteam, data_fmt)
            for i, d in enumerate(sorted_dates):
                count = group_data[key].get(d, 0)
                worksheet.write(r, FIXED_COLS + i, count or '', num_fmt)
                date_totals[d] += count
            worksheet.write(r, FIXED_COLS + len(sorted_dates), row_total, num_fmt)
            grand_total += row_total
            r += 1

        worksheet.merge_range(r, 0, r, FIXED_COLS - 1, 'TOTAL', total_label_fmt)
        for i, d in enumerate(sorted_dates):
            worksheet.write(r, FIXED_COLS + i, date_totals[d] or '', total_num_fmt)
        worksheet.write(r, FIXED_COLS + len(sorted_dates), grand_total, total_num_fmt)


    def _generate_agent_count_sheet(self, workbook, leads, colombo_tz):
        worksheet = workbook.add_worksheet("Agent Report")

        title_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter'})
        hdr_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#BDD7EE', 'border': 1})
        agent_fmt = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1})
        num_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        total_agent_fmt = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})
        total_num_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})

        agent_data = defaultdict(lambda: defaultdict(int))
        agent_names = {}
        all_dates = set()

        for lead in leads:
            uid = lead.user_id.id if lead.user_id else 0
            agent_names[uid] = lead.user_id.name if lead.user_id else 'Unassigned'
            local_dt = pytz.utc.localize(lead.create_date).astimezone(colombo_tz)
            date_str = local_dt.strftime('%m/%d/%Y')
            all_dates.add(date_str)
            agent_data[uid][date_str] += 1

        sorted_dates = sorted(all_dates, key=lambda d: datetime.strptime(d, '%m/%d/%Y'))
        sorted_uids = sorted(agent_names.keys(), key=lambda uid: agent_names[uid])
        total_cols = 1 + len(sorted_dates) + 1  # agent + dates + TOTAL

        title = f"Leads by Agent - {self._period_label()} - ({self._shift_label()})"
        worksheet.merge_range(0, 0, 0, total_cols - 1, title, title_fmt)
        worksheet.set_row(0, 25)

        worksheet.write(1, 0, 'AGENT', hdr_fmt)
        for i, d in enumerate(sorted_dates):
            worksheet.write(1, 1 + i, d, hdr_fmt)
        worksheet.write(1, 1 + len(sorted_dates), 'TOTAL', hdr_fmt)

        worksheet.set_column(0, 0, 20)
        for col in range(1, total_cols):
            worksheet.set_column(col, col, 10)

        date_totals = defaultdict(int)
        grand_total = 0
        r = 2

        for uid in sorted_uids:
            row_total = sum(agent_data[uid].values())
            worksheet.write(r, 0, agent_names[uid], agent_fmt)
            for i, d in enumerate(sorted_dates):
                count = agent_data[uid].get(d, 0)
                worksheet.write(r, 1 + i, count or '', num_fmt)
                date_totals[d] += count
            worksheet.write(r, 1 + len(sorted_dates), row_total, num_fmt)
            grand_total += row_total
            r += 1

        worksheet.write(r, 0, 'TOTAL', total_agent_fmt)
        for i, d in enumerate(sorted_dates):
            worksheet.write(r, 1 + i, date_totals[d] or '', total_num_fmt)
        worksheet.write(r, 1 + len(sorted_dates), grand_total, total_num_fmt)