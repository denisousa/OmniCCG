import os
import re

class RubyBlackHoleSanitizer:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def sanitize_percent_arrays(self):
        """
        Converts %w|...| to ["..."]
        """
        def replace_words(match):
            content = match.group(1)
            words = content.split()
            return '[' + ', '.join([f'"{w}"' for w in words]) + ']'

        # Catches all common delimiters: (), {}, [], ||
        self.content = re.sub(r'%w\s*[\|\{\[\(](.*?)[\|\} মৌসুম\)]', replace_words, self.content, flags=re.DOTALL)

    def sanitize_regex_literals(self):
        """
        Converts /regex/im to "REGEX_LITERAL".
        CRITICAL FIX: Now consumes modifiers (i, m, x, o) after the closing slash.
        """
        # Looks for common regex literals in Ruby (preceded by (, =, space, match)
        # Group 2 ([a-z]*) captures the 'i', 'm', etc. and removes them.
        
        # Case 1: Function argument or assignment: (, /.../flags) or = /.../flags
        self.content = re.sub(r'([(=,])\s*/([^/\n]+)/([a-z]*)', r'\1 "REGEX_LITERAL"', self.content)
        
        # Case 2: match(/.../flags)
        self.content = re.sub(r'match\s*\(\s*/([^/\n]+)/([a-z]*)', r'match("REGEX_LITERAL"', self.content)
        
        # Case 3: ~ /.../flags (match operator)
        self.content = re.sub(r'=~\s*/([^/\n]+)/([a-z]*)', r'=~ "REGEX_LITERAL"', self.content)

    def sanitize_reserved_keywords_methods(self):
        """
        Renames methods that use reserved keywords.
        E.g.: 'def for' breaks the parser. Becomes 'def _for_safe'.
        """
        keywords = ['for', 'end', 'class', 'module', 'while', 'until', 'if', 'unless', 'case']
        
        for kw in keywords:
            # Replace 'def kw' with 'def _kw_safe'
            # \b ensures we don't replace 'def format' with 'def _for_safemat'
            pattern = fr'def\s+{kw}\b'
            replacement = f'def _{kw}_safe'
            self.content = re.sub(pattern, replacement, self.content)

    def sanitize_singleton_class(self):
        self.content = self.content.replace('class << self', 'class SelfSingleton')

    def sanitize_rspec_structure(self):
        """
        Simplifies the RSpec structure to avoid 'Parse Time Limit Exceeded'.
        NiCad understands 'def' much better than nested blocks.
        
        Transforms:
            it "does something" do ... end
        Into:
            def it_does_something ... end
        """
        # 1. Remove description strings from 'it' and transform into function name
        def replacer(match):
            # match.group(1) is the type (it, context, describe)
            # match.group(2) is the description string
            desc = match.group(2)
            # Clean the description to make it a valid variable name
            clean_desc = re.sub(r'[^a-zA-Z0-9_]', '_', desc)
            return f"def {match.group(1)}_{clean_desc}"

        # Regex: looks for (it|context|describe) "string" do
        pattern = r'\b(it|context|describe)\s+"([^"]+)"\s+do'
        self.content = re.sub(pattern, replacer, self.content)
        
        # 2. Remove complex 'should' and 'expect' calls that cause noise
        # lambda { ... }.should raise_error -> just the block
        self.content = re.sub(r'lambda\s*\{', 'proc {', self.content) # lambda is sometimes a special keyword

    def sanitize_interpolation_and_symbols(self):
        # #{...} -> VAR
        self.content = re.sub(r'#\{.*?\}', 'VAR', self.content)
        
        # Fix possible syntax issues from mixed old/new hash syntax left dirty by regex
        # : key => val (extra space caused by previous deletions)
        self.content = re.sub(r':\s+([a-zA-Z_]+)\s+=>', r':\1 =>', self.content)

    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(self.content)

def clean_file_rb(filepath):
    try:
        sanitizer = RubyBlackHoleSanitizer(filepath)
        
        # EXECUTION ORDER
        sanitizer.sanitize_percent_arrays()          # 1. Remove %w
        sanitizer.sanitize_regex_literals()          # 2. Remove /regex/flags (FIXED)
        sanitizer.sanitize_reserved_keywords_methods() # 3. Fix 'def for' (FIXED)
        sanitizer.sanitize_singleton_class()         # 4. Fix class << self
        sanitizer.sanitize_interpolation_and_symbols() # 5. Clean strings
        sanitizer.sanitize_rspec_structure()         # 6. Flatten RSpec to avoid Timeout
        
        sanitizer.save()
        print(f"[OK] Cleaned: {filepath}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed {filepath}: {e}")
        return False

def process_directory_rb(directory):
    count = 0
    errors = 0
    print(f"Starting BLACK HOLE RUBY cleaning in: {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".rb"):
                path = os.path.join(root, file)
                if clean_file_rb(path):
                    count += 1
                else:
                    errors += 1
    print(f"\nDone. Cleaned: {count}, Errors: {errors}")
