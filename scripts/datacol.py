import os
import time
from copy import copy
import xml.etree.ElementTree as etree

# Project settings
GIT_URL = "https://github.com/apache/thrift.git" # The URL of the git repository to clone.
COMMIT_INTERVAL = 10       # How often a commit should be analysed (put 1 for every commit)
MAX_COMMITS = 10           # Maximum number of commits to analyse
USE_ICLONES = False         # Also use iClones to detect clones
LANGUAGE = "java"             # Language extension of project ("java" of "c")

# Directories
SCRIPT_DIR = "scripts"
TOOLS_DIR = "tools"
RES_DIR = "results"
CUR_RES_DIR = RES_DIR + "/0000000"
WS_DIR = "workspace"
REPO_DIR = WS_DIR + "/repo"
DATA_DIR = WS_DIR + "/dataset"
PROD_DATA_DIR = DATA_DIR + "/production"
TEST_DATA_DIR = DATA_DIR + "/test"

# Files
HIST_FILE = WS_DIR + "/githistory.txt"
P_RES_FILE = RES_DIR + "/production_results.xml"
T_RES_FILE = RES_DIR + "/test_results.xml"
P_DENS_FILE = RES_DIR + "/production_density.csv"
T_DENS_FILE = RES_DIR + "/test_density.csv"

# Data
P_LIN_DATA = []
T_LIN_DATA = []
P_DENS_DATA = []
T_DENS_DATA = []

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

    def countLOC(self):
        return (self.le - self.ls)

class CloneClass():
    def __init__(self):
        self.fragments = []

    def contains(self, fragment):
        for f in self.fragments:
            if f.matches(fragment):
                return True
        return False

    def matches(self, cc):
        n = 0
        for fragment in cc.fragments:
            if self.contains(fragment):
                n+=1
        return (n == len(cc.fragments)) or (n == len(self.fragments))

    def toXML(self):
        s = "\t\t<class nclones=\"%d\">\n" % (len(self.fragments))
        for fragment in self.fragments:
            s += fragment.toXML()
        s += "\t\t</class>\n"
        return s

    def countLOC(self):
        count = 0
        for fragment in self.fragments:
            count += fragment.countLOC()
        return count

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

class Lineage():
    def __init__(self):
        self.versions = []

    def matches(self, cc):
        for fragment in cc.fragments:
            if self.versions[-1].cloneclass.contains(fragment):
                return True
        return False

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

def getDataFromCSV(filename):
    try:
        with open(filename, 'r+') as file:
            data = []
            for line in file.readlines():
                data.append((int(line.split(",")[0]), float(line.split(",")[1]), float(line.split(",")[2])))
            return data
    except Exception as e:
        printError("Something went wrong while parsing the CSV file:")
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

def GetCloneFragment(filename, startline, endline):
    lines = [""]
    with open(filename[3:]) as fp:
        remove_ws = False
        for i, line in enumerate(fp):
            if i > (startline - 1): # Start getting lines
                if line.split("//")[0].isspace(): # skip comment-only lines
                    continue
                l = line.split("//")[0] # strip comments after code
                l = l.rstrip()# remove ws after last character
                if remove_ws: # if this line needs to be un-indented
                    l = l.lstrip() # remove ws before first character
                    remove_ws = False
                if len(l) > 2 and l[-1] not in ";{": # if this line was split -> unsplit
                    remove_ws = True
                else: # if not, add endline
                    l = l + "\n"
                lines.append(l)
            if i == (endline - 2): # End getting lines
                break
    return "".join(lines)

def GetPattern(v1, v2):
    evolution = "None"
    if len(v1.fragments) == len(v2.fragments):
        evolution = "Same"
    elif len(v1.fragments) > len(v2.fragments):
        evolution = "Subtract"
    else:
        evolution = "Add"

    change = "None"
    if evolution == "Same" or evolution == "Subtract":
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
    elif evolution == "Add":
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

def SetupRepo():
    print("Setting up workspace for git repository " + GIT_URL)
    # Check if the workspace, repo, and .git directories exist
    if os.path.exists(WS_DIR) and os.path.exists(REPO_DIR) and os.path.exists(REPO_DIR + "/.git"):
        # Check if the current repo is the correct repo
        current_url = os.popen('git --git-dir workspace/repo/.git config --get remote.origin.url').read()
        if GIT_URL in current_url:
            print("The requested repo is already present.\n Repository setup complete.\n")
            return
        else:
            printWarning("Incorrect repo found:\n\t" + current_url)
            print(" > Clearing workspace...")
            os.system('rm -rf ' + WS_DIR) # Clean workspace
    os.system('mkdir ' + WS_DIR) # Make directory for workspace
    os.system('mkdir ' + REPO_DIR) # Make directory for REPO
    os.system('git clone ' + GIT_URL + ' ' + REPO_DIR) # Clone REPO
    print(" Repository setup complete.\n")

def PrepareGitHistory():
    print("Getting git history")
    # Check if the history file exists
    if os.path.exists(HIST_FILE):
        os.system('rm ' + HIST_FILE) # Remove history file
    os.system('(cd ' + REPO_DIR +'; git checkout master -f > /dev/null 2>&1)')
    os.system('git --git-dir workspace/repo/.git log --first-parent --oneline --full-history --sparse > ' + HIST_FILE)
    print(" Git history file updated.\n")

def GetHashes():
    hashes = []
    with open(HIST_FILE) as fp:
        for line in fp:
            hashes.append(line.split()[0])
    hashes.reverse()
    return hashes

def PrepareSourceCode():
    print("Preparing source code")
    # Check if the dataset directory exists
    if os.path.exists(DATA_DIR):
        os.system('rm -rf ' + DATA_DIR)

    os.system('mkdir ' + DATA_DIR) # Make the dataset directory
    os.system('mkdir ' + PROD_DATA_DIR) # Make the production code directory
    os.system('mkdir ' + TEST_DATA_DIR) # Make the test code directory

    # Copy all production files to the production directory
    os.system('for i in `find . -iname \'*.' + LANGUAGE + '\' | grep -vi \"test\"` ; do cp $i ' + PROD_DATA_DIR + '; done')

    # Copy all test files to the test directory
    os.system('for i in `find . -iname \'*.' + LANGUAGE + '\' | grep -i \"test\"` ; do cp $i ' + TEST_DATA_DIR + '; done')
    print(" Source code ready for clone analysis.\n")

def StartFromPreviousVersion():
    # Check if the results directory exists
    if not os.path.exists(RES_DIR):
        os.system('mkdir ' + RES_DIR)
        return 0
    elif os.path.exists(P_RES_FILE) and os.path.exists(P_DENS_FILE) and os.path.exists(T_RES_FILE) and os.path.exists(T_DENS_FILE):
        printInfo("Previous version found.\n")

        print(" Importing data from " + P_RES_FILE)
        global P_LIN_DATA
        P_LIN_DATA = parseLineageFile(P_RES_FILE)
        if not len(P_LIN_DATA):
            printError("Empty production data: no linages found in " + P_RES_FILE)
            return -1

        print(" Importing data from " + T_RES_FILE)
        global T_LIN_DATA
        T_LIN_DATA = parseLineageFile(T_RES_FILE)
        if not len(T_LIN_DATA):
            printError("Empty production data: no linages found in " + T_RES_FILE)
            return -1

        print(" Importing data from " + P_DENS_FILE)
        global P_DENS_DATA
        P_DENS_DATA = getDataFromCSV(P_DENS_FILE)
        if not len(P_DENS_DATA):
            printError("Empty production data: no density evolution found in " + P_DENS_FILE)
            return -1

        print(" Importing data from " + T_DENS_FILE)
        global T_DENS_DATA
        T_DENS_DATA = getDataFromCSV(T_DENS_FILE)
        if not len(T_DENS_DATA):
            printError("Empty test data: no density evolution found in " + T_DENS_DATA)
            return -1

        if P_DENS_DATA[-1][0] != T_DENS_DATA[-1][0]:
            printError("Total number of commits differ between production and test code. ")
            return -1

        printInfo("  >> Resuming data collection from last version.\n")
        return P_DENS_DATA[-1][0]

    return 0

def RunCloneDetection():
    print("Starting clone detection:")
    os.system('mkdir ' + CUR_RES_DIR)

    print(" > Production code:")
    print(" >>> Running nicad4...")
    os.system('(cd ' + TOOLS_DIR + '/NiCad; ./nicad4 functions ' + LANGUAGE + ' ../../' + PROD_DATA_DIR  + '/ > /dev/null 2>&1)')

    if (USE_ICLONES):
        print(" >>> Running iClones...")
        os.system('/opt/unibremen_clone_tools/iclones-0.1.2/iclones.sh -input ' + PROD_DATA_DIR + ' -language ' + LANGUAGE + ' -outformat text -output ' + CUR_RES_DIR +'/iclones_production_results.txt / > /dev/null 2>&1')

    print(" > Test code:")
    print(" >>> Running nicad4...")
    os.system('(cd ' + TOOLS_DIR + '/NiCad; ./nicad4 functions ' + LANGUAGE + ' ../../' + TEST_DATA_DIR + '/ > /dev/null 2>&1)')

    if (USE_ICLONES):
        print(" >>> Running iClones...")
        os.system('/opt/unibremen_clone_tools/iclones-0.1.2/iclones.sh -input ' + TEST_DATA_DIR + ' -language ' + LANGUAGE + ' -outformat text -output ' + CUR_RES_DIR +'/iclones_test_results.txt / > /dev/null 2>&1')

    # Move output to resuls dir
    os.system('mv ' + DATA_DIR + '/production_functions.xml ' + CUR_RES_DIR)
    os.system('mv ' + DATA_DIR + '/test_functions.xml ' + CUR_RES_DIR)
    os.system('mv ' + PROD_DATA_DIR + '_functions-clones/*.xml ' + CUR_RES_DIR)
    os.system('mv ' + TEST_DATA_DIR + '_functions-clones/*.xml ' + CUR_RES_DIR)

    # Clean up
    os.system('rm -rf ' + PROD_DATA_DIR + '_functions-clones')
    os.system('rm -rf ' + TEST_DATA_DIR + '_functions-clones')
    os.system('rm ' + DATA_DIR + '/*.log')
    print(" Finished clone detection.\n")

def parseFunctionsFile(functions_filename):
    functions_dict = {}
    with open(functions_filename, 'r+') as file:
        element = False
        key = ""
        for line in file:
            if element:
                functions_dict[key] = line.split('(')[0].split()[-1]
                element = False
            if len(line.split()) > 0 and "<source" == line.split()[0]:
                xml_element = etree.fromstring(line+"</source>")
                key = CloneFragment(xml_element.get("file"), int(xml_element.get("startline")), int(xml_element.get("endline")))
                element = True
    return functions_dict

def parseNicadCloneClassFile(cloneclass_filename, functions_dict):
    cloneclasses = []
    with open(cloneclass_filename, 'r+') as file:
        # try to parse the xml file
        try:
            file_xml = etree.parse(file)
            # transform each pair in python objects for easy comparison
            for child in file_xml.getroot():
                cc = CloneClass()
                fragments = child.getchildren()
                if not fragments:
                    continue
                for fragment in fragments:
                    cf = CloneFragment(fragment.get("file"), int(fragment.get("startline")), int(fragment.get("endline")))
                    cf.function_name = functions_dict[cf]
                    cf.function_hash = hash(GetCloneFragment(cf.file[3:], cf.ls, cf.le))
                    cc.fragments.append(cf)
                cloneclasses.append(cc)
        except Exception as e:
            printError("Something went wrong while parsing the nicad clonepair dataset:")
            raise e
            return []
    return cloneclasses

def parseIClonesCloneClassFile(cloneclass_filename, cloneclasses, functions_dict):
    code_path = "../../workspace/dataset/"
    if "production" in cloneclass_filename:
        code_path += "production/"
    else:
        code_path += "test/"
    with open(cloneclass_filename, 'r+') as file:
        # try to parse the iclones result file
        cc = None
        for line in file:
            if "CloneClass" == line.split()[0]:
                if cc != None:
                    found = False
                    for cloneclass in cloneclasses:
                        if cc.matches(cloneclass):
                            found = True
                            break
                    if not found and len(cc.fragments) > 1:
                        cloneclasses.append(cc)
                cc = CloneClass()
            elif (cc != None):
                data = line.split()
                cf_temp = CloneFragment(code_path +  data[1], int(data[2]), int(data[3]))
                for function in functions_dict.keys():
                    if function.contains(cf_temp) or cf_temp.contains(function):
                        cf = copy(function)
                        cf.function_name = functions_dict[function]
                        cf.function_hash = hash(GetCloneFragment(cf.file[3:], cf.ls, cf.le))
                        cc.fragments.append(cf)
                        break

def CheckDoubleMatch(cc_original, cc1, cc2):
    """
    Function that checks which cloneclass (cc1 or cc2) matches more strictly with the original cloneclass (cc_original):
        * returns 1 if cc1 matches more strictly
        * returns 2 if cc2 matches more strictly
        * returns 0 if both match the same amount
    """
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

def RunDensityAnalysis(commitNr,  pcloneclasses, tcloneclasses):
    print("Starting density analysis:")
    print(" > Production code...")
    total_amount_of_p_functions = int(os.popen('grep "/source" ' + CUR_RES_DIR + '/production_functions.xml | wc -l').read())
    amount_of_cloned_p_functions = int(os.popen('grep "/source" ' + CUR_RES_DIR + '/production_functions-clones-0.30-classes.xml | wc -l').read())
    density_f_p = 100 * (float(amount_of_cloned_p_functions) / total_amount_of_p_functions)

    cloc_p_out = os.popen('perl tools/cloc/cloc-1.72.pl workspace/dataset/production/ | grep "SUM"').read().split()
    total_amount_of_p_loc = int(cloc_p_out[-1]) + int(cloc_p_out[-2]) + int(cloc_p_out[-3])
    amount_of_cloned_p_loc = 0
    for cloneclass in pcloneclasses:
        amount_of_cloned_p_loc += cloneclass.countLOC()
    density_loc_p = 100 * (float(amount_of_cloned_p_loc) / total_amount_of_p_loc)

    P_DENS_DATA.append((commitNr, density_f_p, density_loc_p))

    print(" > Test code...")
    total_amount_of_t_functions = int(os.popen('grep "/source" ' + CUR_RES_DIR + '/test_functions.xml | wc -l').read())
    amount_of_cloned_t_functions = int(os.popen('grep "/source" ' + CUR_RES_DIR + '/test_functions-clones-0.30-classes.xml | wc -l').read())
    density_f_t = 0
    if (total_amount_of_t_functions != 0):
        density_f_t = 100 * (float(amount_of_cloned_t_functions) / total_amount_of_t_functions)

    total_amount_of_t_loc = 0
    cloc_t_out = os.popen('perl tools/cloc/cloc-1.72.pl workspace/dataset/test/ | grep "SUM"').read().split()
    if (len(cloc_t_out) > 3):
        total_amount_of_t_loc = int(cloc_t_out[-1]) + int(cloc_t_out[-2]) + int(cloc_t_out[-3])
    amount_of_cloned_t_loc = 0
    for cloneclass in tcloneclasses:
        amount_of_cloned_t_loc += cloneclass.countLOC()
    density_loc_t = 0
    if (amount_of_cloned_t_loc != 0):
        density_loc_t = 100 * (float(amount_of_cloned_t_loc) / total_amount_of_t_loc)

    T_DENS_DATA.append((commitNr, density_f_t, density_loc_t))
    print(" Finished density analysis.\n")

def RunGenealogyAnalysis(commitNr, hash):
    print("Starting genealogy analysis:")
    print(" > Production code...")
    pfunctions_dict = parseFunctionsFile(CUR_RES_DIR + "/production_functions.xml")
    pcloneclasses = parseNicadCloneClassFile(CUR_RES_DIR + "/production_functions-clones-0.30-classes.xml", pfunctions_dict)
    if (USE_ICLONES):
        parseIClonesCloneClassFile(CUR_RES_DIR +'/iclones_production_results.txt', pcloneclasses, pfunctions_dict)
    if not P_LIN_DATA: # If there is no lineage data for production yet
        for pcc in pcloneclasses:
            v = CloneVersion(pcc, hash, commitNr)
            l = Lineage()
            l.versions.append(v)
            P_LIN_DATA.append(l)
    else:
        for pcc in pcloneclasses:
            found = False
            for lineage in P_LIN_DATA: # Search for the lineage this cloneclass is part of
                if lineage.matches(pcc):

                    if lineage.versions[-1].nr == commitNr: # special case: another clone class has already been matched in this commit
                        if (len(lineage.versions) < 2):
                            continue
                        checkDoubleMatch = CheckDoubleMatch(lineage.versions[-2].cloneclass, lineage.versions[-1].cloneclass, pcc)
                        if checkDoubleMatch == 1:
                            continue
                        elif checkDoubleMatch == 2:
                            pcloneclasses.append(lineage.versions[-1].cloneclass)
                            lineage.versions.pop()

                    evolution, change = GetPattern(lineage.versions[-1].cloneclass, pcc)
                    if evolution == "Same" and change == "Same" and lineage.versions[-1].evolution_pattern == "Same" and lineage.versions[-1].change_pattern == "Same":
                        lineage.versions[-1].nr = commitNr
                        lineage.versions[-1].hash = hash
                    else:
                        lineage.versions.append(CloneVersion(pcc, hash, commitNr, evolution, change))
                    found = True
                    break
            if not found: # There is no lineage yet for this cloneclass, start a new lineage
                v = CloneVersion(pcc, hash, commitNr)
                l = Lineage()
                l.versions.append(v)
                P_LIN_DATA.append(l)

    print(" > Test code...")
    tfunctions_dict = parseFunctionsFile(CUR_RES_DIR + "/test_functions.xml")
    tcloneclasses = parseNicadCloneClassFile(CUR_RES_DIR + "/test_functions-clones-0.30-classes.xml", tfunctions_dict)
    if (USE_ICLONES):
        parseIClonesCloneClassFile(CUR_RES_DIR +'/iclones_test_results.txt', tcloneclasses, tfunctions_dict)
    if not T_LIN_DATA: # If there is no lineage data for test yet
        for tcc in tcloneclasses:
            v = CloneVersion(tcc, hash, commitNr)
            l = Lineage()
            l.versions.append(v)
            T_LIN_DATA.append(l)
    else:
        for tcc in tcloneclasses:
            found = False
            for lineage in T_LIN_DATA: # Search for the lineage this cloneclass is part of
                if lineage.matches(tcc):

                    if lineage.versions[-1].nr == commitNr: # special case: another clone class has already been matched in this commit
                        if (len(lineage.versions) < 2):
                            continue
                        checkDoubleMatch = CheckDoubleMatch(lineage.versions[-2].cloneclass, lineage.versions[-1].cloneclass, tcc)
                        if checkDoubleMatch == 1:
                            continue
                        elif checkDoubleMatch == 2:
                            tcloneclasses.append(lineage.versions[-1].cloneclass)
                            lineage.versions.pop()

                    evolution, change = GetPattern(lineage.versions[-1].cloneclass, tcc)
                    if evolution == "Same" and change == "Same" and lineage.versions[-1].evolution_pattern == "Same" and lineage.versions[-1].change_pattern == "Same":
                        lineage.versions[-1].nr = commitNr
                        lineage.versions[-1].hash = hash
                    else:
                        lineage.versions.append(CloneVersion(tcc, hash, commitNr, evolution, change))
                    found = True
                    break
            if not found: # There is no lineage yet for this cloneclass, start a new lineage
                v = CloneVersion(tcc, hash, commitNr)
                l = Lineage()
                l.versions.append(v)
                T_LIN_DATA.append(l)
    print(" Finished genealogy analysis.\n")

    # Run clone density analysis
    RunDensityAnalysis(commitNr, pcloneclasses, tcloneclasses)

def WriteLineageFile(lineages, filename):
    output_file = open(filename, "w+")
    output_file.write("<lineages>\n")
    for lineage in lineages:
        output_file.write(lineage.toXML())
    output_file.write("</lineages>\n")
    output_file.close()

def WriteDensityFile(densitys, filename):
    output_file = open(filename, "w+")
    for density in densitys:
        output_file.write(str(density[0]) + ', ' + str(density[1]) + ', ' + str(density[2]) + '\n')
    output_file.close()

def timeToString(seconds):
    result = ""
    hours=seconds//3600
    minutes=(seconds%3600)//60
    seconds=(seconds%3600)%60
    if (hours):
        result += str(hours) + " hours, "
    if (minutes):
        result += str(minutes) + " minutes, "
    result += str(seconds) + " seconds"
    return result

def DataCollection():
    print("STARTING DATA COLLECTION SCRIPT\n")
    SetupRepo()
    PrepareGitHistory()
    hashes = GetHashes()
    time.sleep(1)

    start = StartFromPreviousVersion()
    if start < 0:
        return
    elif start > 0:
        start += COMMIT_INTERVAL
    analysis_index = 0
    total_time = 0
    for hash_index in range(start, len(hashes), COMMIT_INTERVAL):
        iteration_start_time = time.time()
        analysis_index += 1
        current_hash = hashes[hash_index]
        printInfo('Analyzing commit nr.' + str(hash_index) + ' with hash '+ current_hash)
        global CUR_RES_DIR
        CUR_RES_DIR = RES_DIR + "/" + str(hash_index) + '_' + current_hash

        # Check if maximum number of commits has been analyzed
        if analysis_index > MAX_COMMITS:
            printInfo('Maximum amount of commits has been analyzed. Ending data collection...')
            break

        # Checkout current hash
        if not current_hash in os.popen('git --git-dir workspace/repo/.git show --oneline -s').read():
            os.system('(cd ' + REPO_DIR +'; git checkout ' + current_hash + ' -f > /dev/null 2>&1)')
            time.sleep(1)

        # Run clone detection on current hash
        PrepareSourceCode()
        RunCloneDetection()

        # Run genealogy analysis
        RunGenealogyAnalysis(hash_index, current_hash)

        # Clean-up
        os.system('rm -rf ' + CUR_RES_DIR)

        # time
        iteration_end_time = time.time()
        iteration_time = iteration_end_time - iteration_start_time
        total_time += iteration_time
        print("Iteration finished in " + timeToString(int(iteration_time)))
        print(" >>> Average iteration time: " + timeToString(int(total_time/analysis_index)))
        print(" >>> Estimated remaining time: " + timeToString(int((total_time/analysis_index)*(MAX_COMMITS-analysis_index))))
        time.sleep(1)

    # Write Lineage Data to Files
    WriteLineageFile(P_LIN_DATA, P_RES_FILE)
    WriteLineageFile(T_LIN_DATA, T_RES_FILE)
    WriteDensityFile(P_DENS_DATA, P_DENS_FILE)
    WriteDensityFile(T_DENS_DATA, T_DENS_FILE)
    print("\nDONE")

if __name__ == "__main__":
    DataCollection()
