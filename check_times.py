import gspread
from datetime import date, timedelta
from dateutil import parser
from typing import Dict, List
import time


max_lines = 300
day_zero = date(2024, 9, 23)
today = date.today()
qtr_length = 86  # (days)


class Timesheet():
    # student name
    name : str
    # total hours worked per day
    hours : Dict[date, float]

    def __init__(self, name : str, url : str, gc : gspread.Client):
        self.name = name
        self.daily_hours = {(day_zero + timedelta(i)): 0.0 for i in range(qtr_length)}
        self.weekly_hours = [0.0] * 12  # weeks 0-10, plus finals week
        self.populate(url, gc)
    
    def populate(self, url : str, gc : gspread.Client):
        # first, fetch data from the Google Sheet
        ws = gc.open_by_url(url).get_worksheet(0)
        col_a = [_[0] if _ else '' for _ in ws.get(f'A1:A{max_lines}')]
        col_c = [_[0] if _ else '' for _ in ws.get(f'C1:C{max_lines}')]
        # now parse the data        
        for day_txt, hours in zip(col_a, col_c):
            try:
                day = parser.parse(day_txt).date()
            except ValueError:
                continue
            self.daily_hours[day] += float(hours) if hours else 0.0
        # also calculate weekly hour totals
        for week in range(11):
            self.weekly_hours[week] = sum(self.daily_hours[day_zero + timedelta(week*7 + i)] for i in range(7))
        self.weekly_hours[11] = sum(self.daily_hours[day_zero + timedelta(i)] for i in range(77, qtr_length))
    
    def unlogged_days(self, targ_date : date) -> List[date]:
        return [day for day in self.daily_hours if day < targ_date and self.daily_hours[day] == 0.0]
    
    def zero_weeks(self, targ_date : date) -> List[int]:
        current_week = (targ_date - day_zero).days // 7
        return list(filter(lambda i: self.weekly_hours[i] == 0.0, range(current_week)))
    
    def __repr__(self) -> str:
        return f"<{self.name}>"
    
    def __str__(self) -> str:
        unlogged_days = self.unlogged_days(today)
        zero_weeks = self.zero_weeks(today)
        if unlogged_days or zero_weeks:
            days_str = f"Unlogged days: {len(unlogged_days)}."
            weeks_str = f"Zero weeks: {len(zero_weeks)}."
            status = f"{days_str: ^20} {weeks_str: >15}"
        else:
            status = "OK."
        return f"{(self.name+":"): <30} {status}"


if __name__ == '__main__':
    gc = gspread.oauth()
    today = date.today()

    timesheets = []

    total_students = 0
    students_with_sheets = 0
    with open('timesheets.csv', 'r') as f:
        for line in f:
            # (skip comments and blank lines)
            if line.startswith('#') or not line.strip():
                continue
            total_students += 1
            if ';https' in line:
                name, url = line.strip().split(';',1)
                timesheets.append(Timesheet(name, url, gc))
                time.sleep(2)  # avoid rate limiting

    print("\n".join(str(_) for _ in timesheets))