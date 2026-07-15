"""Convert SYNAPSE_ERP_REPORT.md to a professional PDF using fpdf2."""

import re
from pathlib import Path
from fpdf import FPDF

REPORT_MD = Path(__file__).resolve().parent.parent / "SYNAPSE_ERP_REPORT.md"
OUTPUT_PDF = Path(__file__).resolve().parent.parent / "outputs" / "SynapseERP_Report.pdf"


def sanitize(text):
    """Replace characters not supported by latin-1 / core Helvetica font."""
    replacements = {
        '\u2014': '--',   # em-dash
        '\u2013': '-',    # en-dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '-',    # bullet
        '\u2020': '*',    # dagger
        '\u2122': '(TM)', # trademark
        '\u00a0': ' ',    # non-breaking space
        '\u2192': '->',   # right arrow
        '\u2714': '[X]',  # check mark
        '\u2716': '[X]',  # x mark
        '\u25cf': '*',    # black circle
        '\u25e6': '*',    # white bullet
        '\u2043': '-',    # hyphen bullet
        '\u2666': '<>',   # diamond
        '\u25c6': '<>',   # black diamond
        '\u2502': '|',    # box drawing vertical
        '\u2500': '-',    # box drawing horizontal
        '\u2514': '+',    # box drawing corner
        '\u251c': '+',    # box drawing tee
        '\u2524': '+',    # box drawing tee
        '\u2534': '+',    # box drawing tee
        '\u252c': '+',    # box drawing tee
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove any remaining non-latin-1 characters
    result = []
    for ch in text:
        try:
            ch.encode('latin-1')
            result.append(ch)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)


def strip_markdown_table_line(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    cells = [c.strip() for c in s.split('|')]
    return cells


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(True, 20)
        self._in_code = False
        self._code_lines = []
        self._table_mode = False
        self._table_data = []
        self._table_cols = []

    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, sanitize('SynapseERP -- Project Report'), align='R')
            self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    def write_title(self):
        self.add_page()
        self.set_fill_color(20, 32, 31)
        self.rect(0, 0, 210, 100, 'F')
        self.set_y(28)
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(127, 227, 180)
        self.cell(0, 14, 'SynapseERP', align='C')
        self.ln(16)
        self.set_font('Helvetica', '', 14)
        self.set_text_color(245, 244, 238)
        self.cell(0, 8, sanitize('Multimodal Deep Learning Pipeline for Digitizing Offline Indian MSMEs'), align='C')
        self.ln(18)
        self.set_font('Helvetica', 'I', 11)
        self.set_text_color(182, 193, 189)
        self.cell(0, 8, sanitize('Next.js + FastAPI Full-Stack Platform | MVP Report'), align='C')
        self.ln(14)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(150, 160, 155)
        self.cell(0, 7, 'Generated: 2026-07-15', align='C')

    def section_heading(self, text, level=1):
        self._flush_code()
        self._flush_table()
        text = sanitize(text)
        if level == 1:
            self.ln(6)
            self.set_font('Helvetica', 'B', 18)
            self.set_text_color(20, 32, 31)
            self.cell(0, 10, text)
            self.ln(12)
            self.set_draw_color(31, 122, 91)
            self.set_line_width(0.6)
            self.line(10, self.get_y(), 60, self.get_y())
            self.ln(4)
        elif level == 2:
            self.ln(4)
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(31, 122, 91)
            self.cell(0, 8, text)
            self.ln(10)
        elif level == 3:
            self.ln(3)
            self.set_font('Helvetica', 'B', 12)
            self.set_text_color(37, 95, 153)
            self.cell(0, 7, text)
            self.ln(8)

    def body_text(self, text):
        self._flush_code()
        self._flush_table()
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 50, 48)
        self.multi_cell(0, 5.5, sanitize(text))
        self.ln(2)

    def bold_text(self, text):
        self._flush_code()
        self._flush_table()
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(40, 50, 48)
        self.multi_cell(0, 5.5, sanitize(text))
        self.ln(2)

    def bullet(self, text, indent=10):
        self._flush_code()
        self._flush_table()
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 50, 48)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(4, 5.5, '-')
        self.multi_cell(0, 5.5, sanitize(text))
        self.ln(1)

    def start_code_block(self):
        self._flush_table()
        self._in_code = True
        self._code_lines = []

    def add_code_line(self, line):
        if self._in_code:
            self._code_lines.append(line)

    def _flush_code(self):
        if not self._in_code or not self._code_lines:
            self._in_code = False
            self._code_lines = []
            return
        if self.get_y() > 240:
            self.add_page()
        self.set_fill_color(240, 242, 239)
        self.set_text_color(30, 40, 38)
        self.set_font('Courier', '', 8)
        for line in self._code_lines:
            if self.get_y() > 270:
                self.add_page()
                self.set_fill_color(240, 242, 239)
                self.set_text_color(30, 40, 38)
                self.set_font('Courier', '', 8)
            self.set_x(15)
            self.cell(0, 4.5, '  ' + sanitize(line))
            self.ln(4.5)
        self.ln(3)
        self._in_code = False
        self._code_lines = []

    def start_table(self, align=None):
        self._flush_code()
        self._table_mode = True
        self._table_data = []
        self._table_cols = []

    def add_table_row(self, cells):
        if not self._table_cols:
            self._table_cols = len(cells)
        self._table_data.append(cells)

    def _flush_table(self):
        if not self._table_mode or not self._table_data:
            self._table_mode = False
            self._table_data = []
            return
        ncols = self._table_cols
        page_w = 190
        col_w = page_w / max(ncols, 1)
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(31, 122, 91)
        self.set_text_color(255, 255, 255)
        for cell in self._table_data[0]:
            self.cell(col_w, 7, sanitize(str(cell)[:24]), border=1, fill=True)
        self.ln()
        self.set_font('Helvetica', '', 8)
        self.set_text_color(40, 50, 48)
        fill = False
        for row in self._table_data[1:]:
            if self.get_y() > 265:
                self.add_page()
                self.set_font('Helvetica', 'B', 8)
                self.set_fill_color(31, 122, 91)
                self.set_text_color(255, 255, 255)
                for cell in self._table_data[0]:
                    self.cell(col_w, 7, sanitize(str(cell)[:24]), border=1, fill=True)
                self.ln()
                self.set_font('Helvetica', '', 8)
                self.set_text_color(40, 50, 48)
            if fill:
                self.set_fill_color(245, 244, 238)
            else:
                self.set_fill_color(255, 255, 255)
            for cell in row:
                self.cell(col_w, 6, sanitize(str(cell)[:24]), border=1, fill=True)
            self.ln()
            fill = not fill
        self.ln(4)
        self._table_mode = False
        self._table_data = []

    def separator_line(self):
        self._flush_code()
        self._flush_table()
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        y = self.get_y()
        self.line(10, y, 200, y)
        self.ln(4)

    def checkbox(self, text, checked=False):
        self._flush_code()
        self._flush_table()
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 50, 48)
        mark = '[X]' if checked else '[ ]'
        self.cell(4, 5.5, mark)
        self.multi_cell(0, 5.5, sanitize(text))
        self.ln(1)


def build_pdf():
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.write_title()

    content = REPORT_MD.read_text(encoding='utf-8')
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            pdf._flush_code()
            pdf._flush_table()
            i += 1
            continue

        if stripped.startswith('## '):
            pdf.section_heading(stripped[3:], 2)
            i += 1
            continue
        if stripped.startswith('### '):
            pdf.section_heading(stripped[4:], 3)
            i += 1
            continue
        if stripped.startswith('# ') and not pdf._in_code:
            pdf.section_heading(stripped[2:], 1)
            i += 1
            continue

        if stripped.startswith('```'):
            if pdf._in_code:
                pdf._flush_code()
            else:
                pdf.start_code_block()
            i += 1
            continue

        if pdf._in_code:
            pdf.add_code_line(stripped)
            i += 1
            continue

        if re.match(r'^[\|\s\-:]+$', stripped) and '|' in stripped:
            i += 1
            continue

        if stripped.startswith('|') and stripped.endswith('|') and '|' in stripped:
            cells = strip_markdown_table_line(stripped)
            pdf.start_table()
            pdf.add_table_row(cells)
            i += 1
            while i < len(lines):
                ns = lines[i].strip()
                if ns.startswith('|') and ns.endswith('|') and '|' in ns:
                    pdf.add_table_row(strip_markdown_table_line(ns))
                    i += 1
                else:
                    break
            pdf._flush_table()
            continue

        if stripped.startswith('- '):
            pdf.bullet(stripped[2:])
            i += 1
            continue
        if stripped.startswith('* '):
            pdf.bullet(stripped[2:])
            i += 1
            continue

        if re.match(r'^\d+\. ', stripped):
            pdf._flush_table()
            t = re.sub(r'^\d+\.\s*', '', stripped)
            if '[x]' in t:
                t = t.replace('[x]', '')
                pdf.checkbox(t.strip(), True)
            elif '[ ]' in t:
                t = t.replace('[ ]', '')
                pdf.checkbox(t.strip(), False)
            else:
                pdf.bullet(t)
            i += 1
            continue

        if re.match(r'^-{3,}$', stripped) or re.match(r'^\*{3,}$', stripped):
            pdf.separator_line()
            i += 1
            continue

        pdf._flush_table()
        plain = stripped.replace('**', '')
        if stripped.startswith('**') and stripped.endswith('**'):
            pdf.bold_text(stripped[2:-2])
        else:
            pdf.body_text(plain)
        i += 1

    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PDF))
    print(f"PDF generated: {OUTPUT_PDF}")


if __name__ == '__main__':
    build_pdf()
