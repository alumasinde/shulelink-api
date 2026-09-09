from datetime import date
import asyncio
from openpyxl import load_workbook
from app.modules.data_transfer.academic_years import resolve_import_academic_year
from app.modules.data_transfer.school_structure import DISPLAY_HEADERS, SHEETS, _parse_rows, build_template

def test_school_structure_template_contains_all_import_sheets():
    workbook=load_workbook(build_template(),read_only=True,data_only=True)
    assert workbook.sheetnames[0]=='START HERE';assert workbook.sheetnames[1:]==list(SHEETS.keys());workbook.close()

def test_school_structure_template_headers_are_stable():
    workbook=load_workbook(build_template(),read_only=True,data_only=True)
    for sheet,fields in SHEETS.items():
        headers=[str(v).strip().lower().replace(' (required)','') for v in next(workbook[sheet].iter_rows(values_only=True))]
        assert headers==fields;assert [DISPLAY_HEADERS[f] for f in fields]
    workbook.close()

def test_parser_accepts_empty_valid_workbook():
    workbook=load_workbook(build_template(),read_only=True,data_only=True);parsed,errors=_parse_rows(workbook);workbook.close()
    assert errors==[];assert set(parsed)==set(SHEETS);assert all(rows==[] for rows in parsed.values())
class _AcademicYearCursor:
    def __init__(self):self.calls=[];self.result=None
    async def execute(self,sql,args):
        self.calls.append((sql,args));self.result=None if 'name=%s' in sql else [('2026/2026',)]
    async def fetchone(self):return self.result
    async def fetchall(self):return self.result or []

def test_four_digit_year_resolves_to_calendar_year_academic_year():
    cursor=_AcademicYearCursor();tenant_id='tenant-id'
    name=asyncio.run(resolve_import_academic_year(cursor,tenant_id,2026))
    assert name=='2026/2026';assert cursor.calls[1][1]==(tenant_id,date(2026,1,1),date(2027,1,1),date(2026,1,1),date(2027,1,1))
