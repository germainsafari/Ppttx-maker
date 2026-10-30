"""Native PowerPoint transitions and entrance animations (python-pptx has no API for these, so we write the XML)."""
from lxml import etree
from pptx.oxml.ns import qn

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _insert_after_cSld(slide, el):
    sld = slide._element
    # Schema order: cSld, clrMapOvr, transition, timing, extLst
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    existing = sld.find(el.tag)
    if existing is not None:
        sld.remove(existing)
    if el.tag == qn("p:timing"):
        tr = sld.find(qn("p:transition"))
        if tr is not None:
            anchor = tr
    anchor.addnext(el)


def add_fade_transition(slide, speed: str = "med"):
    el = etree.fromstring(f'<p:transition xmlns:p="{P_NS}" spd="{speed}"><p:fade/></p:transition>')
    _insert_after_cSld(slide, el)


def add_staggered_entrance(slide, shapes, step_ms: int = 220, dur_ms: int = 500, effect: str = "fade"):
    """Shapes fade (or wipe up) in one after another, automatically when the slide appears."""
    shapes = [s for s in shapes if s is not None]
    if not shapes:
        return
    ids = iter(range(3, 10_000))
    pars = []
    for i, shp in enumerate(shapes):
        spid = shp.shape_id
        c_outer, c_eff, c_set, c_anim = next(ids), next(ids), next(ids), next(ids)
        filt = "fade" if effect == "fade" else "wipe(up)"
        preset = 10 if effect == "fade" else 22
        subtype = 0 if effect == "fade" else 4
        node = "afterEffect" if i == 0 else "withEffect"
        pars.append(f"""
<p:par><p:cTn id="{c_outer}" fill="hold"><p:stCondLst><p:cond delay="{i * step_ms}"/></p:stCondLst><p:childTnLst>
  <p:par><p:cTn id="{c_eff}" presetID="{preset}" presetClass="entr" presetSubtype="{subtype}" fill="hold" nodeType="{node}">
    <p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
      <p:set><p:cBhvr><p:cTn id="{c_set}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>
        <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>
        <p:to><p:strVal val="visible"/></p:to></p:set>
      <p:animEffect transition="in" filter="{filt}"><p:cBhvr><p:cTn id="{c_anim}" dur="{dur_ms}"/>
        <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>
    </p:childTnLst></p:cTn></p:par>
</p:childTnLst></p:cTn></p:par>""")
    xml = f"""<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>
<p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>
{''.join(pars)}
</p:childTnLst></p:cTn></p:par>
</p:childTnLst></p:cTn>
<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>
</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>"""
    _insert_after_cSld(slide, etree.fromstring(xml))
