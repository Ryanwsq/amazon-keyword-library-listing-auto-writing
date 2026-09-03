"""Small synthetic package regressions; no business files or outputs are changed."""
import copy
import importlib.util
import io
from pathlib import Path
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

spec=importlib.util.spec_from_file_location('transfer',Path(__file__).with_name('copy_preserved_sheets.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

def pack(parts):
    out=io.BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        for name,value in parts.items():z.writestr(name,value)
    return out.getvalue()

def fixture(source=False):
    m,r,o,c=t.M,t.R,t.O,t.C
    parts={
      'xl/workbook.xml':f'<workbook xmlns="{m}" xmlns:r="{o}"><sheets><sheet name="Keep" sheetId="1" r:id="s1"/><sheet name="Source" sheetId="2" r:id="s2"/></sheets></workbook>',
      'xl/_rels/workbook.xml.rels':f'<Relationships xmlns="{r}"><Relationship Id="s1" Type="{o}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="s2" Type="{o}/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="sst" Type="{o}/sharedStrings" Target="sharedStrings.xml"/></Relationships>',
      'xl/styles.xml':f'<styleSheet xmlns="{m}"><fonts count="1"><font><name val="Arial"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
      'xl/sharedStrings.xml':f'<sst xmlns="{m}" count="1" uniqueCount="1"><si><t>'+('Source text' if source else 'Keep text')+'</t></si></sst>',
      'xl/worksheets/sheet1.xml':f'<worksheet xmlns="{m}"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>',
      'xl/worksheets/sheet2.xml':f'<worksheet xmlns="{m}"><sheetData>'+('<row r="1" ht="30"><c r="A1" s="0" t="s"><v>0</v></c><c r="B1"><f>1+2</f><v>3</v></c><c r="C1"><f>IF(1=0,0,&quot;&quot;)</f></c></row>' if source else '')+'</sheetData></worksheet>',
      '[Content_Types].xml':f'<Types xmlns="{c}"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/></Types>'}
    return {k:v.encode() for k,v in parts.items()}

class TransferTests(unittest.TestCase):
    def setUp(self): self.src=fixture(True);self.dst=fixture(False)
    def run_copy(self): return t.copy_sheets(pack(self.src),pack(self.dst),['Source'])
    def test_preserves_cached_formula_missing_cache_shared_text_and_structure(self):
        out,audit=self.run_copy();data=t.unpack(out)
        self.assertEqual(t.cells(self.src,'xl/worksheets/sheet2.xml'),t.cells(data,'xl/worksheets/sheet2.xml'))
        self.assertEqual(self.dst['xl/worksheets/sheet1.xml'],data['xl/worksheets/sheet1.xml'])
        self.assertEqual(2,audit['sheets'][0]['formulas']);self.assertEqual('not_executed',audit['recalculation'])
    def test_nonempty_target_rejected(self):
        self.dst['xl/worksheets/sheet2.xml']=self.src['xl/worksheets/sheet2.xml']
        with self.assertRaisesRegex(ValueError,'empty placeholder'):self.run_copy()
    def test_opc_parts_use_default_namespaces(self):
        out,_=self.run_copy();data=t.unpack(out)
        self.assertIn(b'<Types xmlns=',data['[Content_Types].xml'])
        self.assertNotIn(b'<ns0:Types',data['[Content_Types].xml'])
        root=t.xml(f'<Relationships xmlns="{t.R}"/>'.encode())
        self.assertIn(b'<Relationships xmlns=',t.encode(root))
    def test_missing_or_duplicate_selection_rejected(self):
        for names in (['Missing'],['Source','Source'],[]):
            with self.subTest(names=names),self.assertRaises(ValueError):t.copy_sheets(pack(self.src),pack(self.dst),names)
    def test_unselected_formula_dependency_rejected(self):
        self.src['xl/worksheets/sheet2.xml']=self.src['xl/worksheets/sheet2.xml'].replace(b'1+2',b'Keep!A1')
        with self.assertRaisesRegex(ValueError,'unselected'):self.run_copy()
    def test_external_dependency_rejected(self):
        self.src['xl/worksheets/sheet2.xml']=self.src['xl/worksheets/sheet2.xml'].replace(b'1+2',b'[outside.xlsx]Keep!A1')
        with self.assertRaisesRegex(ValueError,'external'):self.run_copy()
    def test_default_font_drift_rejected(self):
        self.src['xl/styles.xml']=self.src['xl/styles.xml'].replace(b'Arial',b'Different Font')
        with self.assertRaisesRegex(ValueError,'default cell styles'):self.run_copy()
    def test_markup_compatibility_namespace_mapping_rejected(self):
        self.src['xl/styles.xml']=self.src['xl/styles.xml'].replace(b'<styleSheet ',b'<styleSheet xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" mc:Ignorable="x14" ')
        with self.assertRaisesRegex(ValueError,'Markup compatibility'):self.run_copy()
    def test_chart_part_bytes_and_relationship_closure(self):
        p='xl/worksheets/sheet2.xml';self.src[t.relpath(p)]=f'<Relationships xmlns="{t.R}"><Relationship Id="chart" Type="{t.O}/chart" Target="../drawings/chart.xml"/></Relationships>'.encode()
        self.src['xl/drawings/chart.xml']=b'<chart><cached>original</cached></chart>'
        out,audit=self.run_copy();data=t.unpack(out);item=audit['preserved_raw_parts'][0]
        self.assertEqual(self.src['xl/drawings/chart.xml'],data[item['target']]);self.assertEqual('passed',audit['relationship_closure'])
    def test_defined_name_dependency_rejected(self):
        self.src['xl/workbook.xml']=self.src['xl/workbook.xml'].replace(b'</workbook>',b'<definedNames><definedName name="HiddenDependency">Keep!A1</definedName></definedNames></workbook>')
        with self.assertRaisesRegex(ValueError,'defined names'):self.run_copy()

if __name__=='__main__':unittest.main()
