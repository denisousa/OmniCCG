
def GetPattern(v1, v2, current_hash, parent_hash):
    evolution = GetEvolution(v1, v2, current_hash, parent_hash)

    change = "None"
    if evolution == "Same" or "Subtract" in evolution:
        nr_of_matches = 0
        for f2 in v2.fragments:
            for f1 in v1.fragments:
                if f1.function_hash == f2.function_hash:
                    nr_of_matches += 1
                    break
        if nr_of_matches == len(v2.fragments):
            change = "Same"
        elif nr_of_matches == 0:
            change = "Consistent"
        else:
            change = "Inconsistent"
    elif "Add" in evolution:
        nr_of_matches = 0
        for f1 in v1.fragments:
            for f2 in v2.fragments:
                if f1.function_hash == f2.function_hash:
                    nr_of_matches += 1
                    break
        if nr_of_matches == len(v1.fragments):
            change = "Same"
        elif nr_of_matches == 0:
            change = "Consistent"
        else:
            change = "Inconsistent"

    return (evolution, change)

def RunGenealogyAnalysis(commitNr, hash):
    print("Starting genealogy analysis:")
    print(" > Production code...")
    pcloneclasses = parseCloneClassFile(CLONE_DETECTOR_XML)
    if not P_LIN_DATA: # If there is no lineage data for production yet
        for pcc in pcloneclasses:
            # Here i have the first lineage
            for fragment in pcc.fragments:
                fragment.origin_note = check_commit_for_code(REPO_DIR, fragment, hash)
            v = CloneVersion(pcc, hash, commitNr)
            v.origin = True
            l = Lineage()
            l.versions.append(v)
            P_LIN_DATA.append(l)
    else:
        for pcc in pcloneclasses:
            found = False
            for lineage in P_LIN_DATA:
                # Search for the lineage this cloneclass is part of
                if lineage.matches(pcc):
                    if lineage.versions[-1].move:
                        pcc_was_moved = check_was_moved(pcc, lineage.versions[-1].cloneclass)
                        evolution, change = GetPattern(lineage.versions[-1].cloneclass, pcc, hash, lineage.versions[-1].hash)
                        if pcc_was_moved:
                            v = CloneVersion(pcc, hash, commitNr, evolution, change, False, True)
                        else:
                            v = CloneVersion(pcc, hash, commitNr, evolution, change)
                        lineage.versions.append(v)
                        found = True
                        break

                    pcc_was_moved = check_was_moved(pcc, lineage.versions[-1].cloneclass)
                    if pcc_was_moved:
                        evolution, change = GetPattern(lineage.versions[-1].cloneclass, pcc, hash, lineage.versions[-1].hash)
                        lineage.versions.append(CloneVersion(pcc, hash, commitNr, evolution, change, False, True))
                        found = True
                        break

                    if lineage.versions[-1].nr == commitNr:
                        # special case: another clone class has already been matched in this commit
                        if (len(lineage.versions) < 2):
                            continue
                        checkDoubleMatch = CheckDoubleMatch(lineage.versions[-2].cloneclass, lineage.versions[-1].cloneclass, pcc)
                        if checkDoubleMatch == 1:
                            continue
                        elif checkDoubleMatch == 2:
                            pcloneclasses.append(lineage.versions[-1].cloneclass)
                            lineage.versions.pop()
                            found = True
                            break

                    evolution, change = GetPattern(lineage.versions[-1].cloneclass, pcc, hash, lineage.versions[-1].hash)
                    if evolution == "Same" and change == "Same" and lineage.versions[-1].evolution_pattern == "Same" and lineage.versions[-1].change_pattern == "Same":            
                        # I need check here!
                        lineage.versions[-1].nr = commitNr
                        lineage.versions[-1].hash = hash
                    else:
                        lineage.versions.append(CloneVersion(pcc, hash, commitNr, evolution, change))
                    found = True
                    break

            if not found:
                # There is no lineage yet for this cloneclass, start a new lineage
                for fragment in pcc.fragments:
                    fragment.origin_note = check_commit_for_code(REPO_DIR, fragment, hash)
                v = CloneVersion(pcc, hash, commitNr)
                v.origin = True
                l = Lineage()
                l.versions.append(v)
                P_LIN_DATA.append(l)
        
            # Clone Death
            # new_cc = copy.deepcopy(pcc)
            # v = CloneVersion(new_cc, hash, commitNr)

    print(" Finished genealogy analysis.\n")

    # Run clone density analysis
    #RunDensityAnalysis(commitNr, pcloneclasses)