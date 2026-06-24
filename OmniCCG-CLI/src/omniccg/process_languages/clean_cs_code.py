import os
import re

class CSharpNuclearSanitizer:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def remove_preprocessor_directives(self):
        """
        Remove lines starting with # (e.g.: #if, #region, #nullable).
        This fixes the problem of closing braces after a #endif.
        """
        # Remove the entire line but keep the line break to avoid drastically changing line counts
        self.content = re.sub(r'^\s*#.*$', '', self.content, flags=re.MULTILINE)

    def convert_filescoped_namespace(self):
        """
        Converts 'namespace X;' to 'namespace X { ... }'.
        Since we already removed the #directives, we can safely add the } at the end.
        """
        # Regex to find file-scoped namespace
        pattern = r'^(?P<indent>\s*)namespace\s+(?P<name>[\w\.]+)\s*;'
        match = re.search(pattern, self.content, re.MULTILINE)
        
        if match:
            # Replace with 'namespace X {'
            self.content = re.sub(pattern, f"{match.group('indent')}namespace {match.group('name')} {{", self.content, count=1, flags=re.MULTILINE)
            # Add the closing brace at the end of the file
            if not self.content.endswith('\n'):
                self.content += '\n'
            self.content += '}\n'
            return True
        return False

    def remove_modern_modifiers(self):
        """
        Remove modifiers that confuse old parsers or didn't exist in specific contexts.
        List: public, private, protected, internal, sealed, override, virtual, readonly, static abstract
        """
        # Remove 'static abstract' (C# 11) specifically first
        self.content = re.sub(r'\bstatic\s+abstract\s+', '', self.content)
        
        # Remove common access modifiers.
        # For clone detection, knowing if it's public or private matters little; the method structure matters more.
        modifiers = [
            'public', 'private', 'protected', 'internal', 
            'sealed', 'override', 'virtual', 'readonly', 'async' # async can also be removed to simplify
        ]
        
        # Build regex (e.g.: \bpublic\s+)
        pattern = r'\b(' + '|'.join(modifiers) + r')\s+'
        self.content = re.sub(pattern, '', self.content)

    def clean_generics(self):
        """
        Remove 'in' and 'out' from generic definitions.
        E.g.: interface I<out T> -> interface I<T>
        """
        # This is a bit rough, removes 'out ' and 'in ' if preceded by '<' or ','
        # Simplified example to catch common cases
        self.content = re.sub(r'(<|,)\s*(out|in)\s+', r'\1 ', self.content)

    def remove_nullables(self):
        """
        Remove '?' from nullable types.
        E.g.: string? -> string
        """
        # Remove ? if it immediately follows a word (type) and is not a ternary operator (space after)
        # Regex: word followed by ?
        self.content = re.sub(r'(?<=\w)\?', '', self.content)

    def remove_attributes(self):
        """
        Attempts to remove attributes [Key], [Required], etc.
        This is hard to do perfectly with regex, but we remove simple single-line cases.
        """
        self.content = re.sub(r'^\s*\[.+\]\s*$', '', self.content, flags=re.MULTILINE)

    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(self.content)

def clean_file_cs(filepath):
    try:
        sanitizer = CSharpNuclearSanitizer(filepath)
        
        # ORDER MATTERS
        sanitizer.remove_preprocessor_directives() # 1. Remove #if so it doesn't interfere with namespace
        sanitizer.remove_attributes()              # 2. Remove attributes
        sanitizer.convert_filescoped_namespace()   # 3. Fix namespace
        sanitizer.remove_modern_modifiers()        # 4. Remove static abstract, public, etc
        sanitizer.clean_generics()                 # 5. Clean <out T>
        sanitizer.remove_nullables()               # 6. Remove string?
        
        sanitizer.save()
        print(f"[OK] Cleaned: {filepath}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed {filepath}: {e}")
        return False

def process_directory_cs(directory):
    count = 0
    errors = 0
    print(f"Starting NUCLEAR C# cleaning in: {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".cs"):
                path = os.path.join(root, file)
                if clean_file_cs(path):
                    count += 1
                else:
                    errors += 1
    print(f"\nDone. Cleaned: {count}, Errors: {errors}")
