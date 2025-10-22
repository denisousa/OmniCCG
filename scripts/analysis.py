from __future__ import division
import xml.etree.ElementTree as etree


# Directories
RES_DIRS = ["java/apache_avro", "java/apache_math", "java/eclipse", "java/google", "c/apache_apr", "c/cairo", "c/libarchive", "c/libsodium"]

# Output functions
def printWarning(message):
    print('\033[93m WARNING: ' + message + '\033[0m')

def printError(message):
    print('\033[91m ERROR: ' + message + '\033[0m')

def printInfo(message):
    print('\033[96m INFO: ' + message + '\033[0m')

# Classes
class CloneFragment():
    def __init__(self, file, ls, le, fn = "", fh = 0):
        self.file = file
        self.ls = ls
        self.le = le
        self.function_name = fn
        self.function_hash = fh

    def contains(self, other):
        return self.file == other.file and self.ls <= other.ls and self.le >= other.le

    def __eq__(self, other):
        return self.file == other.file and self.ls == other.ls and self.le == other.le

    def matches(self, other):
        return self.file == other.file and self.function_name == other.function_name

    def matchesStrictly(self, other):
        return self.file == other.file and self.function_name == other.function_name and (self.ls == other.ls or self.function_hash == other.function_hash)

    def __hash__(self):
        return hash(self.file+str(self.ls))

    def toXML(self):
        return "\t\t\t<source file=\"%s\" startline=\"%d\" endline=\"%d\" function=\"%s\" hash=\"%d\"></source>\n" % (self.file, self.ls, self.le,self.function_name, self.function_hash)

class CloneClass():
    def __init__(self):
        self.fragments = []

    def contains(self, fragment):
        for f in self.fragments:
            if f.matches(fragment):
                return True
        return False

    def toXML(self):
        s = "\t\t<class nclones=\"%d\">\n" % (len(self.fragments))
        for fragment in self.fragments:
            s += fragment.toXML()
        s += "\t\t</class>\n"
        return s

class CloneVersion():
    def __init__(self, cc, h, n, evo = "None", chan = "None"):
        self.cloneclass = cc
        self.hash = h
        self.nr = n
        self.evolution_pattern = evo
        self.change_pattern = chan

    def toXML(self):
        s = "\t<version nr=\"%d\" hash=\"%s\" evolution=\"%s\" change=\"%s\">\n" % (self.nr, self.hash, self.evolution_pattern, self.change_pattern)
        s += self.cloneclass.toXML()
        s += "\t</version>\n"
        return s

    def getMatchScore(self, version):
        score = 0
        for fragment1 in self.cloneclass.fragments:
            found = False
            for fragment2 in version.cloneclass.fragments:
                if fragment1.matchesStrictly(fragment2):
                    found = True
                    break
            if found:
                score += 2
            else:
                for fragment2 in version.cloneclass.fragments:
                    if fragment1.matches(fragment2):
                        score += 1
                        break
        return score

class Lineage():
    def __init__(self):
        self.versions = []

    def matches(self, cc):
        for fragment in cc.fragments:
            if self.versions[-1].cloneclass.contains(fragment):
                return True
        return False

    def containsInconsistentChange(self):
        for version in self.versions:
            if version.change_pattern == "Inconsistent":
                return True
        return False

    def countInconsistentChange(self):
        count = 0
        for version in self.versions:
            if version.change_pattern == "Inconsistent":
                count+=1
        return count

    def containsConsistentChange(self):
        for version in self.versions:
            if version.change_pattern == "Consistent":
                return True
        return False

    def countConsistentChange(self):
        count = 0
        for version in self.versions:
            if version.change_pattern == "Consistent":
                count+=1
        return count

    def containsDoubleVersions(self):
        n_prev = -1
        for version in self.versions:
            if version.nr == n_prev:
                return True
            else:
                n_prev = version.nr
        return False

    def getLength(self):
        return (self.versions[-1].nr - self.versions[0].nr)

    def toXML(self):
        s = "<lineage>\n"
        for version in self.versions:
            s += version.toXML()
        s += "</lineage>\n"
        return s

def getLastCommitFromDensityCSV(filename):
    try:
        with open(filename, 'r+') as file:
            return int(file.readlines()[-1].split(",")[0])
    except Exception as e:
        printError("Something went wrong while parsing the density dataset:")
        printError(str(e))
        return 0

def parseLineageFile(filename):
    lineages = []
    with open(filename, 'r+') as file:
        # try to parse the xml file
        try:
            file_xml = etree.parse(file)
            # transform each pair in python objects for easy comparison
            for lineage in file_xml.getroot():
                lin = Lineage()
                versions = lineage.getchildren()
                for version in versions:
                    cc = CloneClass()
                    cloneclasses = version.getchildren()
                    if len(cloneclasses) != 1:
                        printWarning("Unexpected amount of clone classes in version.")
                        printWarning("Please check if inputfile is consistent.")
                    for fragment in cloneclasses[0].getchildren():
                        cc.fragments.append(CloneFragment(fragment.get("file"), int(fragment.get("startline")), int(fragment.get("endline")), fragment.get("function"), int(fragment.get("hash"))))
                    cv = CloneVersion(cc, version.get("hash"), int(version.get("nr")), version.get("evolution"), version.get("change"))
                    lin.versions.append(cv)
                lineages.append(lin)
        except Exception as e:
            printError("Something went wrong while parsing the lineage dataset:")
            printError(str(e))
            return []
    return lineages

def getNrOfInconsistentChangeLineages(lineages):
    count = 0
    for lineage in lineages:
        if lineage.containsInconsistentChange():
            count+=1
    return count

def getNrOfConsistentChangeLineages(lineages):
    count = 0
    for lineage in lineages:
        if lineage.containsConsistentChange() and not lineage.containsInconsistentChange():
            count+=1
    return count

def examineChangeLineages(lineages):
    consistent = []
    inconsistent = []
    inconsistent2 = []
    for lineage in lineages:
        if lineage.containsConsistentChange() and not lineage.containsInconsistentChange():
            consistent.append(lineage.countConsistentChange())
        elif lineage.containsInconsistentChange():
            inconsistent.append(lineage.countConsistentChange())
            inconsistent2.append(lineage.countInconsistentChange())
    print("CONSISTENT CHANGES IN CONSISTENT LINEAGE:" + overviewStringList(consistent))
    print("CONSISTENT CHANGES IN INCONSISTENT LINEAGE:" + overviewStringList(inconsistent))
    print("INCONSISTENT CHANGES IN INCONSISTENT LINEAGE:" + overviewStringList(inconsistent2))
    print("")

def getNrOfStableLineages(lineages):
    count = 0
    for lineage in lineages:
        if not lineage.containsConsistentChange() and not lineage.containsInconsistentChange():
            count+=1
    return count

def getNrOfAliveLineages(lineages, last_commit_nr):
    count = 0
    for lineage in lineages:
        if lineage.versions[-1].nr == last_commit_nr:
            count+=1
    return count

def getLenghtsOfDeadLineages(lineages, last_commit_nr):
    lengths = []
    for lineage in lineages:
        if lineage.versions[-1].nr != last_commit_nr:
            lengths.append(lineage.getLength())
    return lengths

def countVersions(lineages):
    data = {}
    data["total"] = 0
    data["Consistent"] = 0
    data["Inconsistent"] = 0
    data["Same"] = 0
    data["Add"] = 0
    data["Subtract"] = 0
    for lineage in lineages:
        last_nr = 0
        for version in lineage.versions:
            if version.evolution_pattern == "None" and version.change_pattern == "None":
                last_nr = version.nr
            elif version.evolution_pattern == "Same" and version.change_pattern == "Same":
                num = (version.nr - last_nr)/30
                data[version.evolution_pattern] += num
                data[version.change_pattern] += num
                data["total"] += num
                last_nr = version.nr
            else:
                data[version.evolution_pattern] += 1
                data[version.change_pattern] += 1
                data["total"] += 1
                last_nr = version.nr
    return data

def percentageString(part,total):
    return str(part) + " (" + str((100*part)/total) + "%)"

def percentageStringLatex(part,total):
    return "%0.2f" % ((100*part)/total)

def overviewString2(part1, part2, total, legend):
    return percentageString(part1, total) + " / " + percentageString(part2, total) + " (" + legend + ")"

def overviewString2Latex(part1, part2, total, legend):
    return percentageStringLatex(part1, total) + " \% & " + percentageStringLatex(part2, total) + "\% (" + legend + ")"

def overviewString3(part1, part2, part3, total, legend):
    return percentageString(part1, total) + " / " + percentageString(part2, total) + " / "+  percentageString(part3, total) + " (" + legend + ")"

def overviewString3Latex(part1, part2, part3, total, legend):
    return percentageStringLatex(part1, total) + "\% & " + percentageStringLatex(part2, total) + "\% & "+  percentageStringLatex(part3, total) + "\% (" + legend + ")"

def overviewStringList(l):
    return str(min(l)) + " / " + str(sum(l)/len(l)) + " / " + str(max(l)) + " (min/avg/max)"

def recalculate_lineage(lineage):
    for i in range(len(lineage.versions)):
        cur_n = lineage.versions[i].nr
        prev_n = -1
        j = i - 1
        while (j >= 0 and cur_n == prev_n):
            prev_n = lineage.versions[j].nr
            j-=1
        if j != -1:
            # print("REANALYZING: ")
            # print(lineage.versions[i].toXML())
            best_match = lineage.versions[j]
            score = lineage.versions[i].getMatchScore(lineage.versions[j])
            while (j >= 0 and lineage.versions[j].nr == prev_n):
                # print(" >>> POSSIBLE MATCH:")
                # print(lineage.versions[j].toXML())
                if score < lineage.versions[i].getMatchScore(lineage.versions[j]):
                    score = lineage.versions[i].getMatchScore(lineage.versions[j])
                    best_match = lineage.versions[j]
                j-=1
            # print(" <<< FINAL MATCH:")
            # print(best_match.toXML())
            # evolution
            if len(best_match.cloneclass.fragments) == len(lineage.versions[i].cloneclass.fragments):
                lineage.versions[i].evolution_pattern = "Same"
            elif len(best_match.cloneclass.fragments) > len(lineage.versions[i].cloneclass.fragments):
                lineage.versions[i].evolution_pattern = "Subtract"
            else:
                # print("CHANGING TO ADD FROM " + lineage.versions[i].evolution_pattern)

                lineage.versions[i].evolution_pattern = "Add"


            # change
            if score == 2*len(lineage.versions[i].cloneclass.fragments):
                lineage.versions[i].change_pattern = "Same"
            elif score == len(lineage.versions[i].cloneclass.fragments):
                lineage.versions[i].change_pattern = "Consistent"
            else:
                lineage.versions[i].change_pattern = "Inconsistent"

def Analysis(RES_DIR):
    print("STARTING CLONE GENEOLOGY ANALYSIS\n")
    print(RES_DIR)
    # Files
    P_RES_FILE = RES_DIR + "/production_results.xml"
    T_RES_FILE = RES_DIR + "/test_results.xml"
    P_DENS_FILE = RES_DIR + "/production_density.csv"
    T_DENS_FILE = RES_DIR + "/test_density.csv"

    print(" Importing data from " + P_RES_FILE)
    P_LIN_DATA = parseLineageFile(P_RES_FILE)
    if not len(P_LIN_DATA):
        printError("Empty production data: no linages found in " + P_RES_FILE)
        return

    print(" Importing data from " + T_RES_FILE)
    T_LIN_DATA = parseLineageFile(T_RES_FILE)
    if not len(T_LIN_DATA):
        printError("Empty production data: no linages found in " + T_RES_FILE)
        return
    p_last_commit = getLastCommitFromDensityCSV(P_DENS_FILE)
    t_last_commit = getLastCommitFromDensityCSV(T_DENS_FILE)
    if p_last_commit != t_last_commit:
        printError("Total number of commits differ between production and test code. ")
        return
    print("  >> All data imported\n")

    for lineage in P_LIN_DATA:
        if lineage.containsDoubleVersions():
            recalculate_lineage(lineage)

    for lineage in T_LIN_DATA:
        if lineage.containsDoubleVersions():
            recalculate_lineage(lineage)

    print("\n--- RESULTS ---\n")

    print("Total amount of clone lineages")
    print(" - production: " + str(len(P_LIN_DATA)))
    print(" - test:       " + str(len(T_LIN_DATA)))

    print("\nChange patterns of lineages:")
    p_inconsistent = getNrOfInconsistentChangeLineages(P_LIN_DATA)
    t_inconsistent = getNrOfInconsistentChangeLineages(T_LIN_DATA)
    p_consistent = getNrOfConsistentChangeLineages(P_LIN_DATA)
    t_consistent = getNrOfConsistentChangeLineages(T_LIN_DATA)
    p_stable = getNrOfStableLineages(P_LIN_DATA)
    t_stable = getNrOfStableLineages(T_LIN_DATA)
    print(" - production: " + overviewString3Latex(p_consistent, p_stable, p_inconsistent, len(P_LIN_DATA), "consistent/stable/inconsistent"))
    print(" - test:       " + overviewString3Latex(t_consistent, t_stable, t_inconsistent, len(T_LIN_DATA), "consistent/stable/inconsistent"))

    print("\nStatus of clone lineages:")
    p_alive = getNrOfAliveLineages(P_LIN_DATA, p_last_commit)
    t_alive = getNrOfAliveLineages(T_LIN_DATA, t_last_commit)
    p_dead = len(P_LIN_DATA) - p_alive
    t_dead = len(T_LIN_DATA) - t_alive
    print(" - production: " + overviewString2(p_alive, p_dead, len(P_LIN_DATA), "alive/dead"))
    print(" - test:       " + overviewString2(t_alive, t_dead, len(T_LIN_DATA), "alive/dead"))

    print("\nLength of dead clone lineages:")
    p_dead_length = getLenghtsOfDeadLineages(P_LIN_DATA, p_last_commit)
    t_dead_length = getLenghtsOfDeadLineages(T_LIN_DATA, t_last_commit)
    print(" - production: " + overviewStringList(p_dead_length))
    print(" - test:       " + overviewStringList(t_dead_length))
    p_dead_length.sort()
    t_dead_length.sort()
    print(" - production full list:" + str(p_dead_length))
    print(" - test full list:      " + str(t_dead_length))

    print("\nTotal amount of versions:")
    p_data = countVersions(P_LIN_DATA)
    t_data = countVersions(T_LIN_DATA)
    print(" - production: " + str(p_data["total"]))
    print(" - test:       " + str(t_data["total"]))

    print("\nEvolution pattern of versions:")
    p_same_evo = p_data["total"] - p_data["Add"] - p_data["Subtract"]
    t_same_evo = t_data["total"] - t_data["Add"] - t_data["Subtract"]
    print(" - production: " + overviewString2Latex(p_data["Add"], p_data["Subtract"], p_data["Add"]+ p_data["Subtract"], "add/subtract"))
    print(" - test:       " + overviewString2Latex(t_data["Add"], t_data["Subtract"], t_data["Add"]+ t_data["Subtract"], "add/subtract"))

    print("\nChange pattern of versions:")
    p_same_change = p_data["total"] - p_data["Consistent"] - p_data["Inconsistent"]
    t_same_change = t_data["total"] - t_data["Consistent"] - t_data["Inconsistent"]
    print(" - production: " + overviewString2Latex(p_data["Consistent"], p_data["Inconsistent"], p_data["Consistent"] + p_data["Inconsistent"] , "consistent/inconsistent"))
    print(" - test:       " + overviewString2Latex(t_data["Consistent"], t_data["Inconsistent"], t_data["Consistent"] + t_data["Inconsistent"] , "consistent/inconsistent"))
    examineChangeLineages(P_LIN_DATA)
    examineChangeLineages(T_LIN_DATA)

    if (p_same_evo + p_same_change != p_data["Same"]):
        printWarning("Calculated amount of same versions does not match measured amount in production data.")
    if (t_same_evo + t_same_change != t_data["Same"]):
        printWarning("Calculated amount of same versions does not match measured amount in test data.")

    print("\nDONE")

def generateCloneLengthFiles(RES_DIR):
        print("STARTING CLONE LENGTH ANALYSIS\n")
        # Files
        P_RES_FILE = RES_DIR + "/production_results.xml"
        T_RES_FILE = RES_DIR + "/test_results.xml"
        P_DENS_FILE = RES_DIR + "/production_density.csv"
        T_DENS_FILE = RES_DIR + "/test_density.csv"
        NEW_P_RES_FILE = RES_DIR + "/production_clone_length.csv"
        NEW_T_RES_FILE = RES_DIR + "/test_clone_length.csv"

        print(" Importing data from " + P_RES_FILE)
        P_LIN_DATA = parseLineageFile(P_RES_FILE)
        if not len(P_LIN_DATA):
            printError("Empty production data: no linages found in " + P_RES_FILE)
            return

        print(" Importing data from " + T_RES_FILE)
        T_LIN_DATA = parseLineageFile(T_RES_FILE)
        if not len(T_LIN_DATA):
            printError("Empty production data: no linages found in " + T_RES_FILE)
            return
        p_last_commit = getLastCommitFromDensityCSV(P_DENS_FILE)
        t_last_commit = getLastCommitFromDensityCSV(T_DENS_FILE)
        if p_last_commit != t_last_commit:
            printError("Total number of commits differ between production and test code. ")
            return
        print("  >> All data imported\n")

        P_LENS = getLenghtsOfDeadLineages(P_LIN_DATA, p_last_commit)
        T_LENS = getLenghtsOfDeadLineages(T_LIN_DATA, t_last_commit)
        P_LENS.sort()
        T_LENS.sort()

        MAX = max(P_LENS[-1],T_LENS[-1])

        with open(NEW_P_RES_FILE,'w+') as p_out:
            for i in range(0,MAX,10):
                ratio = 0
                for l in P_LENS:
                    if l <= i:
                        ratio+=1
                p_out.write(str(i) + "," + str((100*ratio)/float(len(P_LENS))))
                p_out.write("\n")

        with open(NEW_T_RES_FILE,'w+') as t_out:
            for i in range(0,MAX,10):
                ratio = 0
                for l in T_LENS:
                    if l <= i:
                        ratio+=1
                t_out.write(str(i) + "," + str((100*ratio)/float(len(T_LENS))))
                t_out.write("\n")

if __name__ == "__main__":
    for RES_DIR in RES_DIRS:
        Analysis(RES_DIR)
    #     generateCloneLengthFiles(RES_DIR)
