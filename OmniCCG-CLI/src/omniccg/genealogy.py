from typing import List, Optional, Tuple

from omniccg.models import Context
from omniccg.domain.Lineage import Lineage
from omniccg.domain.CloneClass import CloneClass
from omniccg.domain.CloneVersion import CloneVersion
from omniccg.clone_detection import parseCloneClassFile


def GetPattern(v1: CloneVersion, v2: CloneVersion) -> Tuple[str, str]:
    frags1 = v1.cloneclass.fragments
    frags2 = v2.cloneclass.fragments

    if len(frags1) == len(frags2):
        evolution = "Same"
    elif len(frags1) > len(frags2):
        evolution = "Subtract"
    else:
        evolution = "Add"

    needle, haystack = (frags1, frags2) if evolution == "Add" else (frags2, frags1)
    haystack_hashes = {f.function_hash for f in haystack}
    matches = sum(1 for f in needle if f.function_hash in haystack_hashes)

    if matches == len(needle):
        change = "Same"
    elif matches == 0:
        change = "Consistent"
    else:
        change = "Inconsistent"

    return evolution, change


def _handle_matched_lineage(
    lineage: Lineage, pcc: CloneClass, commitNr: int, hash_: str
) -> Tuple[bool, Optional[CloneClass]]:
    if lineage.versions[-1].nr == commitNr:
        if len(lineage.versions) < 2:
            return True, None
        result = CheckDoubleMatch(
            lineage.versions[-2].cloneclass,
            lineage.versions[-1].cloneclass,
            pcc,
        )
        if result == 1:
            return True, None
        if result == 2:
            displaced = lineage.versions[-1].cloneclass
            lineage.versions.pop()
            return False, displaced

    evolution, change = GetPattern(lineage.versions[-1], CloneVersion(pcc))
    if (
        evolution == "Same"
        and change == "Same"
        and lineage.versions[-1].evolution_pattern == "Same"
        and lineage.versions[-1].change_pattern == "Same"
    ):
        lineage.versions[-1].nr = commitNr
        lineage.versions[-1].hash = hash_
    else:
        lineage.versions.append(CloneVersion(pcc, hash_, commitNr, evolution, change))

    return False, None


def CheckDoubleMatch(cc_original: CloneClass, cc1: CloneClass, cc2: CloneClass) -> int:
    cc1_strict_match = False
    cc2_strict_match = False
    for fragment in cc_original.fragments:
        for f1 in cc1.fragments:
            if fragment.matchesStrictly(f1):
                cc1_strict_match = True
        for f2 in cc2.fragments:
            if fragment.matchesStrictly(f2):
                cc2_strict_match = True
    if cc1_strict_match == cc2_strict_match:
        return 0
    if cc1_strict_match:
        return 1
    elif cc2_strict_match:
        return 2
    return 0


def RunGenealogyAnalysis(ctx: Context, commitNr: int, hash_: str) -> None:
    from omniccg.density import RunDensityAnalysis

    p, st = ctx.paths, ctx.state
    print(f"Extract Code Code Genealogy (CCG) - Hash Commit {hash_}")
    pcloneclasses = parseCloneClassFile(p.clone_detector_xml)

    if not st.p_lin_data:
        for pcc in pcloneclasses:
            lineage = Lineage()
            lineage.versions.append(CloneVersion(pcc, hash_, commitNr))
            st.p_lin_data.append(lineage)
    else:
        for pcc in pcloneclasses:
            found = False
            for lineage in st.p_lin_data:
                if not lineage.matches(pcc):
                    continue
                skip, displaced = _handle_matched_lineage(lineage, pcc, commitNr, hash_)
                if skip:
                    continue
                if displaced is not None:
                    pcloneclasses.append(displaced)
                found = True
                break
            if not found:
                lineage = Lineage()
                lineage.versions.append(CloneVersion(pcc, hash_, commitNr))
                st.p_lin_data.append(lineage)

    RunDensityAnalysis(ctx, commitNr, pcloneclasses)


def WriteLineageFile(ctx: Context, lineages: List[Lineage], filename: str) -> str:
    xml_txt = "<lineages>\n"
    with open(filename, "w+", encoding="utf-8") as output_file:
        output_file.write("<lineages>\n")
        for lineage in lineages:
            output_file.write(lineage.toXML())
            xml_txt += lineage.toXML()
        output_file.write("</lineages>\n")
        xml_txt += "</lineages>\n"
    return xml_txt
