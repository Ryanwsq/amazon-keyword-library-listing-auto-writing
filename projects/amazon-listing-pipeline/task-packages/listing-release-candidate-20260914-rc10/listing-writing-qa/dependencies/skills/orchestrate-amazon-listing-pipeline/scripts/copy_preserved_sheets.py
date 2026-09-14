#!/usr/bin/env python3
"""Copy explicitly selected OOXML sheets into empty, pre-authored placeholders.

User-authorized lossless packaging only: no business recalculation or workbook
authoring fallback. Source hashes, formula caches, styles and relationship closure
are checked. Unsupported workbook-wide dependencies fail closed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/package/2006/relationships'
O='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'m':M}
def tag(n): return '{'+M+'}'+n
def digest(b): return hashlib.sha256(b).hexdigest()
def xml(b): return ET.fromstring(b)
def encode(e):
    # Use the default OPC namespace for compatibility with the tested importer.
    # Keep relationship attributes qualified when serializing spreadsheet parts.
    ET.register_namespace('r',O)
    if e.tag.startswith('{'): ET.register_namespace('',e.tag[1:].split('}')[0])
    return ET.tostring(e,encoding='utf-8',xml_declaration=True)
def relpath(p): return posixpath.join(posixpath.dirname(p),'_rels',posixpath.basename(p)+'.rels')
def resolve(p,target):
    out=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(p),target))
    if out.startswith('../') or out=='..': raise ValueError('Relationship escapes package')
    return out
def unpack(data):
    with ZipFile(io.BytesIO(data)) as z:
        if z.testzip(): raise ValueError('Invalid ZIP')
        return {n:z.read(n) for n in z.namelist()}
def sheets(parts):
    rels={r.attrib['Id']:resolve('xl/workbook.xml',r.attrib['Target']) for r in xml(parts['xl/_rels/workbook.xml.rels'])}
    return {s.attrib['name']:rels[s.attrib['{'+O+'}id']] for s in xml(parts['xl/workbook.xml']).findall('m:sheets/m:sheet',NS)}
def sst(parts):
    return list(xml(parts['xl/sharedStrings.xml'])) if 'xl/sharedStrings.xml' in parts else []
def semantic(e):
    return (e.tag,tuple(sorted(e.attrib.items())),e.text or '',tuple(semantic(x) for x in e))
def cells(parts,p):
    strings=sst(parts);out={}
    for c in xml(parts[p]).findall('.//m:sheetData/m:row/m:c',NS):
        t=c.attrib.get('t');v=c.find('m:v',NS);f=c.find('m:f',NS)
        if t=='s': val=semantic(strings[int(v.text)])
        elif t=='inlineStr': val=semantic(c.find('m:is',NS))
        else: val=v.text if v is not None else None
        if val is not None or f is not None: out[c.attrib['r']]=(t,val,semantic(f) if f is not None else None)
    return out
def ensure(parent,name):
    item=parent.find(tag(name))
    if item is None: item=ET.SubElement(parent,tag(name))
    return item
def set_count(e): e.set('count',str(len(e)))

def merge_styles(src,dst):
    a,b=xml(src['xl/styles.xml']),xml(dst['xl/styles.xml']);maps={}
    def default_style(root):
        x=copy.deepcopy(root.find(tag('cellXfs'))[0]);components=[]
        for attr,collection in [('fontId','fonts'),('fillId','fills'),('borderId','borders'),('xfId','cellStyleXfs')]:
            idx=int(x.attrib.pop(attr,'0'));components.append(semantic(root.find(tag(collection))[idx]))
        return semantic(x),components
    if default_style(a)!=default_style(b):
        raise ValueError('Implicit default cell styles differ; explicit mapping required')
    for n in ('colors','extLst'):
        x,y=a.find(tag(n)),b.find(tag(n))
        if x is not None and (y is None or semantic(x)!=semantic(y)):
            raise ValueError('Unsupported differing global style '+n)
    table=a.find(tag('tableStyles'))
    if table is not None and len(table): raise ValueError('Custom source table styles require explicit supported mapping')
    anum=a.find(tag('numFmts'));bnum=ensure(b,'numFmts')
    codes={x.attrib['formatCode']:int(x.attrib['numFmtId']) for x in bnum}
    fresh=max([163]+[int(x.attrib['numFmtId']) for x in bnum])+1;num={}
    for x in list(anum) if anum is not None else []:
        code=x.attrib['formatCode'];old=int(x.attrib['numFmtId'])
        if code in codes: num[old]=codes[code]
        else:
            y=copy.deepcopy(x);y.set('numFmtId',str(fresh));bnum.append(y);num[old]=fresh;codes[code]=fresh;fresh+=1
    set_count(bnum);maps['numFmtId']=num
    for name,attr in [('fonts','fontId'),('fills','fillId'),('borders','borderId')]:
        aa=a.find(tag(name));bb=ensure(b,name);offset=len(bb);maps[attr]={i:i+offset for i in range(len(aa))}
        bb.extend(copy.deepcopy(list(aa)));set_count(bb)
    def xf(node,with_base):
        y=copy.deepcopy(node)
        for attr in ('fontId','fillId','borderId','numFmtId'):
            if attr in y.attrib:
                old=int(y.attrib[attr]);y.set(attr,str(maps[attr].get(old,old)))
        if with_base and 'xfId' in y.attrib: y.set('xfId',str(maps['xfId'][int(y.attrib['xfId'])]))
        return y
    for name,attr,base in [('cellStyleXfs','xfId',False),('cellXfs','s',True)]:
        aa=a.find(tag(name));bb=ensure(b,name);offset=len(bb);maps[attr]={i:i+offset for i in range(len(aa))}
        bb.extend(xf(x,base) for x in aa);set_count(bb)
    ad=a.find(tag('dxfs'));bd=ensure(b,'dxfs');offset=len(bd);maps['dxfId']={i:i+offset for i in range(len(ad) if ad is not None else 0)}
    for x in list(ad) if ad is not None else []:
        y=copy.deepcopy(x)
        for n in y.iter(tag('numFmt')):
            old=int(n.attrib['numFmtId']);n.set('numFmtId',str(num.get(old,old)))
        bd.append(y)
    set_count(bd)
    ac=a.find(tag('cellStyles'));bc=ensure(b,'cellStyles');names={x.attrib.get('name') for x in bc}
    for x in list(ac) if ac is not None else []:
        y=copy.deepcopy(x);y.set('xfId',str(maps['xfId'][int(y.attrib['xfId'])]));name=y.attrib.get('name','Style')
        if name in names:
            y.set('name','Preserved_'+str(len(bc))+'_'+name)
            y.attrib.pop('builtinId',None)
        names.add(y.attrib['name']);bc.append(y)
    set_count(bc)
    # CT_Stylesheet child order must remain legal after adding missing collections.
    order=['numFmts','fonts','fills','borders','cellStyleXfs','cellXfs','cellStyles','dxfs','tableStyles','colors','extLst']
    b[:]=sorted(list(b),key=lambda e:order.index(e.tag.split('}')[-1]) if e.tag.split('}')[-1] in order else 99)
    dst['xl/styles.xml']=encode(b)
    return maps

def copy_sheets(source_bytes,target_bytes,names):
    src,dst=unpack(source_bytes),unpack(target_bytes);original_dst=dict(dst)
    sm,tm=sheets(src),sheets(dst)
    if not names or len(names)!=len(set(names)): raise ValueError('Explicit unique sheet selection required')
    if any(n not in sm or n not in tm for n in names): raise ValueError('Missing source sheet or target placeholder')
    for part in ['xl/styles.xml','xl/sharedStrings.xml']+[sm[n] for n in names]:
        if part not in src: continue
        for node in xml(src[part]).iter():
            if any(k.startswith('{http://schemas.openxmlformats.org/markup-compatibility/2006}') for k in node.attrib):
                raise ValueError('Markup compatibility namespace mappings require explicit support')
    if xml(src['xl/workbook.xml']).find('m:definedNames',NS) is not None:
        raise ValueError('Source defined names need an explicit dependency mapping')
    # Theme colors/fonts are workbook-global; reject drift instead of recoloring source.
    themes=lambda p:[v for k,v in p.items() if k.startswith('xl/theme/') and k.endswith('.xml')]
    if [semantic(xml(x)) for x in themes(src)]!=[semantic(xml(x)) for x in themes(dst)]:
        raise ValueError('Source and target themes differ; no silent theme conversion')
    for name in names:
        p=tm[name]
        if cells(dst,p) or relpath(p) in dst: raise ValueError('Target sheet must be an empty placeholder: '+name)
        root=xml(src[sm[name]])
        for f in root.findall('.//m:f',NS):
            text=f.text or ''
            if '[' in text or ('!' in text and not re.findall(r"(?:'((?:[^']|'')+)'|([A-Za-z_\u0080-\uffff][\w\u0080-\uffff .]*))!",text)):
                raise ValueError('Unsupported external or ambiguous formula dependency')
            for quoted,plain in re.findall(r"(?:'((?:[^']|'')+)'|([A-Za-z_\u0080-\uffff][\w\u0080-\uffff .]*))!",text):
                if (quoted.replace("''","'") or plain) not in names:
                    raise ValueError('Formula depends on an unselected source sheet')
    maps=merge_styles(src,dst)
    strings=sst(dst);offset=len(strings);strings.extend(copy.deepcopy(sst(src)))
    if strings:
        root=ET.Element(tag('sst'));root.extend(strings);set_count(root);root.set('uniqueCount',str(len(strings)));dst['xl/sharedStrings.xml']=encode(root)
        rels=xml(dst['xl/_rels/workbook.xml.rels'])
        if not any(r.attrib['Type'].endswith('/sharedStrings') for r in rels):
            ET.SubElement(rels,'{'+R+'}Relationship',{'Id':'preservedSST','Type':O+'/sharedStrings','Target':'/xl/sharedStrings.xml'})
            dst['xl/_rels/workbook.xml.rels']=encode(rels)
    prefix='xl/preserved_'+digest(source_bytes)[:12]+'/'
    mapping={sm[n]:tm[n] for n in names};visited=set();raw_parts=[]
    def transfer(p):
        if p in visited:return mapping[p]
        if p not in src:raise ValueError('Missing source part '+p)
        out=mapping.setdefault(p,prefix+p);visited.add(p)
        if out in dst and p not in {sm[n] for n in names}:raise ValueError('Destination part collision')
        data=src[p]
        if p in {sm[n] for n in names}:
            root=xml(data)
            for n in root.iter():
                if n.tag in (tag('c'),tag('row')) and 's' in n.attrib:n.set('s',str(maps['s'][int(n.attrib['s'])]))
                if n.tag==tag('col') and 'style' in n.attrib:n.set('style',str(maps['s'][int(n.attrib['style'])]))
                if 'dxfId' in n.attrib:n.set('dxfId',str(maps['dxfId'][int(n.attrib['dxfId'])]))
                if n.tag==tag('c') and n.attrib.get('t')=='s':
                    v=n.find(tag('v'));v.text=str(int(v.text)+offset)
            data=encode(root)
        else:
            if p.endswith('.xml') and xml(data).tag==tag('table'):
                raise ValueError('Source structured tables need explicit unique table-ID/name mapping')
            raw_parts.append((p,out,digest(data)))
        dst[out]=data
        rp=relpath(p)
        if rp in src:
            rels=xml(src[rp])
            for rel in rels:
                if rel.attrib.get('TargetMode')=='External':
                    if not rel.attrib['Type'].endswith('/hyperlink'):raise ValueError('Unsupported external relationship')
                    continue
                child=resolve(p,rel.attrib['Target']);rel.set('Target','/'+transfer(child))
            dst[relpath(out)]=encode(rels)
        return out
    for name in names:transfer(sm[name])
    types=xml(dst['[Content_Types].xml']);stypes=xml(src['[Content_Types].xml'])
    overrides={x.attrib['PartName'] for x in types if x.tag.endswith('Override')};defaults={x.attrib['Extension']:x.attrib['ContentType'] for x in types if x.tag.endswith('Default')}
    source_types={x.attrib['PartName'].lstrip('/'):x.attrib['ContentType'] for x in stypes if x.tag.endswith('Override')}
    for x in stypes:
        if x.tag.endswith('Default'):
            ext=x.attrib['Extension']
            if ext in defaults and defaults[ext]!=x.attrib['ContentType']:raise ValueError('Content-type default collision')
            if ext not in defaults:types.append(copy.deepcopy(x));defaults[ext]=x.attrib['ContentType']
    for p,out in mapping.items():
        if p in source_types and '/'+out not in overrides:
            ET.SubElement(types,'{'+C+'}Override',{'PartName':'/'+out,'ContentType':source_types[p]});overrides.add('/'+out)
    if strings and '/xl/sharedStrings.xml' not in overrides:
        ET.SubElement(types,'{'+C+'}Override',{'PartName':'/xl/sharedStrings.xml','ContentType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml'})
    dst['[Content_Types].xml']=encode(types)
    if strings:
        root=xml(dst['xl/sharedStrings.xml']);count=sum(1 for p in tm.values() for c in xml(dst[p]).findall('.//m:c',NS) if c.attrib.get('t')=='s');root.set('count',str(count));dst['xl/sharedStrings.xml']=encode(root)
    # Closed-package checks. Other existing sheets must not change at all.
    for n,p in tm.items():
        if n not in names and dst[p]!=original_dst[p]:raise AssertionError('Unselected target sheet changed')
    stats=[]
    for name in names:
        if cells(src,sm[name])!=cells(dst,tm[name]):raise AssertionError('Value/formula/cache drift: '+name)
        # Reverse the allowed style/SST remaps and compare the entire worksheet tree.
        root=xml(dst[tm[name]]);rev_s={v:k for k,v in maps['s'].items()};rev_d={v:k for k,v in maps['dxfId'].items()}
        for n in root.iter():
            if n.tag in (tag('c'),tag('row')) and 's' in n.attrib:n.set('s',str(rev_s[int(n.attrib['s'])]))
            if n.tag==tag('col') and 'style' in n.attrib:n.set('style',str(rev_s[int(n.attrib['style'])]))
            if 'dxfId' in n.attrib:n.set('dxfId',str(rev_d[int(n.attrib['dxfId'])]))
            if n.tag==tag('c') and n.attrib.get('t')=='s':v=n.find(tag('v'));v.text=str(int(v.text)-offset)
        if semantic(root)!=semantic(xml(src[sm[name]])):raise AssertionError('Worksheet structure/style drift')
        stats.append({'sheet':name,'cells':len(cells(src,sm[name])),'formulas':len(root.findall('.//m:f',NS)),'source_part':sm[name],'target_part':tm[name]})
    for p,out,h in raw_parts:
        if digest(dst[out])!=h:raise AssertionError('Preserved chart/drawing/binary changed')
    for p,data in dst.items():
        if not p.endswith('.rels'):continue
        owner='' if p=='_rels/.rels' else posixpath.join(posixpath.dirname(posixpath.dirname(p)),posixpath.basename(p)[:-5])
        for rel in xml(data):
            if rel.attrib.get('TargetMode')!='External' and resolve(owner,rel.attrib['Target']) not in dst:raise ValueError('Broken relationship '+p)
    out=io.BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        for p,data in dst.items():z.writestr(p,data)
    audit={'source_sha256':digest(source_bytes),'target_before_sha256':digest(target_bytes),'output_sha256':digest(out.getvalue()),'sheets':stats,'preserved_raw_parts':[{'source':p,'target':q,'sha256':h} for p,q,h in raw_parts],'formula_cache_value_style_structure_checks':'passed','relationship_closure':'passed','recalculation':'not_executed','style_maps':maps}
    return out.getvalue(),audit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','target','output','expected-source-sha256','expected-target-sha256','run-id','audit-json'):p.add_argument('--'+key,required=True)
    p.add_argument('--sheet',action='append',required=True);a=p.parse_args()
    source,target=Path(a.source).resolve(),Path(a.target).resolve();output=Path(a.output).resolve();audit_path=Path(a.audit_json).resolve()
    if output in (source,target) or output.exists() or audit_path.exists():raise ValueError('Write a new output/audit path; originals must be preserved')
    sb,tb=source.read_bytes(),target.read_bytes()
    if digest(sb)!=a.expected_source_sha256 or digest(tb)!=a.expected_target_sha256:raise ValueError('Source/target SHA-256 mismatch')
    result,audit=copy_sheets(sb,tb,a.sheet);audit['run_id']=a.run_id
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.sheet-copy-',dir=output.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(result)
        os.replace(tmp,output)
    except Exception:
        if os.path.exists(tmp):os.unlink(tmp)
        raise
    audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    if digest(source.read_bytes())!=a.expected_source_sha256 or digest(target.read_bytes())!=a.expected_target_sha256:raise AssertionError('Original changed')
    print(json.dumps({'output':str(output),'sha256':audit['output_sha256'],'sheet_count':len(a.sheet),'formula_count':sum(x['formulas'] for x in audit['sheets']),'status':'COPY_VERIFIED_NO_RECALC'},ensure_ascii=False))

if __name__=='__main__':main()
