import gspread
import re
from datetime import date, timedelta
from dateutil import parser

gc = gspread.oauth()

total_students = 0
students_with_sheets = 0
with open('timesheets.csv', 'r') as f:
    names_and_timesheet_urls = []
    for line in f:
        if line.startswith('#'):
            continue
        total_students += 1
        if ';https' in line:
            name, url = line.strip().split(';',1)
            names_and_timesheet_urls.append((name, url))
            students_with_sheets += 1

print(f'{students_with_sheets}/{total_students} have shared timesheets.')
print()

MAXLINE = 300


def fetch_logs(sheet_url):
    ws = gc.open_by_url(sheet_url).get_worksheet(0)
    col_a = [_[0] if _ else '' for _ in ws.get(f'A1:A{MAXLINE}')]
    col_c = [_[0] if _ else '' for _ in ws.get(f'C1:C{MAXLINE}')]
    return col_a, col_c


def get_unlogged_days(col_a, col_c, targ_date):
    # Flag all dates strictly before targ_date where col_c is empty
    checked_days = {}
    unlogged_days = []
    for (i, day_cell) in enumerate(col_a):
        # make sure it's a date cell
        try:
            day = parser.parse(day_cell).date()
        except ValueError:
            continue  # skip non-date cells in col A
        if day < targ_date:
            if day not in checked_days:
                checked_days[day] = set()
            checked_days[day].add(col_c[i])
    # now that we've gathered all days before targ_date,
    # flag the days whose only value is ''
    for day in checked_days:
        if len(checked_days[day]) == 1 and '' in checked_days[day]:
            unlogged_days.append(day.strftime('%B %d'))
    return unlogged_days


def get_zero_weeks(col_a, col_c, targ_date):
    week_totals = []
    week_total_re = re.compile(r'Week \d+ total hours')
    for i in range(len(col_a)):
        if week_total_re.match(col_a[i]) or col_a[i] == 'Finals Week total hours':
            week_totals.append(col_c[i])
    assert(len(week_totals) == 12)  # weeks 0-10, plus finals week  
    zero_weeks = []
    for i in range(len(week_totals)):
        if targ_date >= date(2021, 9, 23) + timedelta(weeks=i):
            if not week_totals[i]:
                zero_weeks.append(f'Week {i}' if i < 11 else 'Finals week')
    return zero_weeks


def validate_cols(name, col_a, col_c, targ_date):
    name = ' '.join(name.split(',')[::-1])
    unlogged_days = get_unlogged_days(col_a, col_c, targ_date)
    zero_weeks = get_zero_weeks(col_a, col_c, targ_date)
    if not unlogged_days and not zero_weeks:
        summary = f'{name}: OK.'
    else:
        summary = f'{name}: Missing data...'
    report = [summary]
    if unlogged_days:
        report.append(f'  {len(unlogged_days)} unlogged days:')
        for day in unlogged_days:
            report.append(f'    {day}')
    if zero_weeks:
        report.append(f'  {len(zero_weeks)} weeks with 0 hours:')
        for week in zero_weeks:
            report.append(f'    {week}')
    return '\n'.join(report)


def validate(name, sheet_url, targ_date):
    report = validate_cols(name, *fetch_logs(sheet_url), targ_date)
    print(report)


if __name__ == '__main__':
    today = date.today()
    for (name, url) in names_and_timesheet_urls:
        validate(name, url, today)