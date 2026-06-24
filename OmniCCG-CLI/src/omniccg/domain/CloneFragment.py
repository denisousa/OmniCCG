from .code_operations import get_code_without_comments_and_blank_lines
from .hash_operations import generate_simhash, match_hashes

class CloneFragment:
    def __init__(self, file, ls, le, function_name="", function_hash=0):
        # replace /dataset/production with /repo to keep compatibility with the original pipeline
        self.file = file.replace("/dataset/production", "/repo")
        self.ls = ls
        self.le = le
        self.function_name = function_name or ""
        self.code_content = get_code_without_comments_and_blank_lines(file, ls, le)
        self.hash = generate_simhash(self.code_content)
        self.function_hash = function_hash or self.hash

    def contains(self, other):
        return self.file == other.file and self.ls <= other.ls and self.le >= other.le

    def __eq__(self, other):
        return self.file == other.file and self.ls == other.ls and self.le == other.le

    def matches(self, other):
        if self.function_name and other.function_name:
            return self.file == other.file and self.function_name == other.function_name

        if self.file == other.file and self.ls == other.ls and self.le == other.le:
            return True

        matches_result, _ = match_hashes(self.hash, other.hash, threshold=0.90)
        return matches_result

    def matchesStrictly(self, other):
        if self.function_name and other.function_name:
            same_name = self.file == other.file and self.function_name == other.function_name
            return same_name and (self.ls == other.ls or self.function_hash == other.function_hash)

        matches_result, _ = match_hashes(self.hash, other.hash, threshold=1.0)
        return self.file == other.file and matches_result

    def __hash__(self):
        return hash(self.file + str(self.ls))

    def toXML(self):
        return '\t\t\t<source file="%s" startline="%d" endline="%d" function_name="%s" hash="%d"></source>\n' % (
            self.file,
            self.ls,
            self.le,
            self.function_name,
            self.function_hash,
        )

    def countLOC(self):
        return self.le - self.ls
