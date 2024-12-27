import base64
import io
import pytz
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter
from collections import defaultdict


class CRMLeadReport(models.TransientModel):
    _name = 'crm.lead.report'
    _description = 'Generate Excel Report for Leads'

    report_by = fields.Selection(
        [('date', 'Date'), ('range', 'Date Range')],
        string="Report By", required=True, default='date'
    )
    start_date = fields.Date(string="Date", required=True)
    end_date = fields.Date(string="End Date")
    shift_type = fields.Selection(
        [('day', 'Day'), ('night', 'Night'), ('both', 'Both')],
        string="Shift Type", required=True, default='day'
    )

    def action_generate_report(self):
        colombo_tz = pytz.timezone('Asia/Colombo')

        if not self.end_date:
            self.end_date = self.start_date
        if self.start_date > self.end_date:
            raise UserError(_("Start Date cannot be greater than End Date."))

        leads = self.env['crm.lead'].search([
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ], order='create_date desc')
        if not leads:
            raise UserError(_("No leads found for the selected period."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        self._generate_leads_sheet(workbook, leads, colombo_tz)

        self._generate_summary_sheet(workbook, leads)

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

    def _generate_leads_sheet(self, workbook, leads, colombo_tz):
        worksheet = workbook.add_worksheet("Leads Report")

        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'bg_color': '#F0F0F0', 'border': 1
        })
        data_format = workbook.add_format({'align': 'left', 'border': 1})

        headers = ['Lead Name', 'Salesperson', 'Create Date Time', 'Attend Time', 'Response Time (minutes)']
        worksheet.set_column(0, 0, 60)
        worksheet.set_column(1, 1, 25)
        worksheet.set_column(2, 2, 25)
        worksheet.set_column(3, 3, 25)
        worksheet.set_column(4, 4, 25)

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        for row, lead in enumerate(leads, start=1):
            response_time = lead.response_time if lead.response_time else 'N/A'
            create_date_str = self._convert_to_local_time(lead.create_date, colombo_tz)
            attend_time_str = self._convert_to_local_time(lead.attend_time, colombo_tz)

            worksheet.write(row, 0, lead.name or 'N/A', data_format)
            worksheet.write(row, 1, lead.user_id.name or 'Unassigned', data_format)
            worksheet.write(row, 2, create_date_str, data_format)
            worksheet.write(row, 3, attend_time_str, data_format)
            worksheet.write(row, 4, round(response_time, 2) if response_time != 'N/A' else 'N/A', data_format)

    def _generate_summary_sheet(self, workbook, leads):
        worksheet = workbook.add_worksheet("Summary Report")

        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'bg_color': '#FFD700', 'border': 1
        })
        data_format = workbook.add_format({'align': 'left', 'border': 1})
        numeric_format = workbook.add_format({'align': 'center', 'border': 1})
        green_format = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#C6EFCE'})
        yellow_format = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#FFEB9C'})
        red_format = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#FFC7CE'})

        worksheet.write(0, 0, "Attend Time Range", header_format)
        worksheet.write(0, 1, "Count", header_format)
        worksheet.write(0, 2, "Percentage", header_format)
        worksheet.set_column(0, 0, 30)
        worksheet.set_column(1, 1, 25)
        worksheet.set_column(2, 2, 25)

        response_categories = {
            '0-5': 0,
            '5-15': 0,
            'over_15': 0,
            'not_attended': 0
        }

        for lead in leads:
            if lead.response_time:
                if lead.response_time <= 5:
                    response_categories['0-5'] += 1
                elif lead.response_time <= 15:
                    response_categories['5-15'] += 1
                else:
                    response_categories['over_15'] += 1
            else:
                response_categories['not_attended'] += 1

        total_leads = len(leads)
        percentage_0_5 = (response_categories['0-5'] / total_leads) * 100 if total_leads else 0

        row = 1
        response_time_ranges = ['0-5 minutes', '5-15 minutes', 'Over 15 minutes', 'Not Attended']

        for idx, range_label in enumerate(response_time_ranges, start=1):
            count = response_categories['0-5'] if range_label == '0-5 minutes' else \
                    response_categories['5-15'] if range_label == '5-15 minutes' else \
                    response_categories['over_15'] if range_label == 'Over 15 minutes' else \
                    response_categories['not_attended']

            percentage = (count / total_leads) * 100 if total_leads else 0

            worksheet.write(row, 0, range_label, data_format)
            worksheet.write(row, 1, count, numeric_format)
            worksheet.write(row, 2, f"{percentage:.2f}%", numeric_format)
            row += 1

        worksheet.write(row + 2, 0, "Overall Percentage (0-5 mins)", header_format)
        format_to_use = green_format if percentage_0_5 >= 85 else yellow_format if percentage_0_5 >= 50 else red_format
        worksheet.write(row + 2, 1, f"{percentage_0_5:.2f}%", format_to_use)

    # def _generate_summary_sheet(self, workbook, leads):
    #     """Generate the summary sheet."""
    #     worksheet = workbook.add_worksheet("Summary Report")
    #
    #     # Styles
    #     header_format = workbook.add_format({
    #         'bold': True, 'align': 'center', 'bg_color': '#FFD700', 'border': 1
    #     })
    #     data_format = workbook.add_format({'align': 'left', 'border': 1})
    #     numeric_format = workbook.add_format({'align': 'center', 'border': 1})
    #
    #     # Prepare summary data
    #     summary_data = defaultdict(lambda: defaultdict(int))
    #     for lead in leads:
    #         shift = 'Day' if lead.create_date.hour < 18 else 'Night'
    #         salesperson = lead.user_id.name or 'Unassigned'
    #         summary_data[salesperson][shift] += 1
    #
    #     # Headers
    #     headers = ['Salesperson', 'Day Leads', 'Night Leads', 'Total']
    #     worksheet.set_column(0, 0, 30)
    #     worksheet.set_column(1, 3, 15)
    #     for col, header in enumerate(headers):
    #         worksheet.write(0, col, header, header_format)
    #
    #     # Fill data
    #     row = 1
    #     for salesperson, shifts in summary_data.items():
    #         day_leads = shifts.get('Day', 0)
    #         night_leads = shifts.get('Night', 0)
    #         total_leads = day_leads + night_leads
    #
    #         worksheet.write(row, 0, salesperson, data_format)
    #         worksheet.write(row, 1, day_leads, numeric_format)
    #         worksheet.write(row, 2, night_leads, numeric_format)
    #         worksheet.write(row, 3, total_leads, numeric_format)
    #         row += 1

    def _convert_to_local_time(self, datetime_field, timezone):
        """Convert a UTC datetime field to local timezone and format it."""
        if datetime_field:
            local_time = pytz.utc.localize(datetime_field).astimezone(timezone)
            return local_time.strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'
