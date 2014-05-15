#!/usr/bin/env python

# Copyright (C) 2013 met.no
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""A simple documentation tool for creating HTML documents from collections of
Python packages and modules.
"""

import ast, glob, os, sys

class Module:

    """Represents a module file containing AST objects obtained by using the
    ast module's parser."""
    
    def __init__(self, name, objects):
    
        self.name = name
        self.objects = objects

class Package:

    """Represents a package directory containing modules and other package
    directories."""

    def __init__(self, name, objects):
    
        self.name = name
        self.objects = objects

class Index:

    """Compiles an index of objects that can be referenced in docstrings.
    """
    
    def __init__(self):
    
        # Compile a dictionary of references.
        self.refs = {}
        
        # Maintain a context stack to allow references to be as close as
        # possible to the context in which they are used.
        self.context = []
    
    def is_documented(self, obj):
    
        if obj.__class__ in Writer.CheckDocstring:
            return ast.get_docstring(obj)
        else:
            return True
    
    def read(self, obj):
    
        """Reads the Module or Package object specified by obj, calling the
        appropriate method to handle it."""
        
        if isinstance(obj, Module):
            self.read_module(obj)
        elif isinstance(obj, Package):
            self.read_package(obj)
    
    def read_module(self, module):
    
        """Reads and processes the specified module and its contents."""
        
        self.name = module.name
        self.process(module.objects)
    
    def read_package(self, package):
    
        """Reads and processes the specified package and its contents."""
        
        # Append the Package object to the context because this has a name
        # attribute that various methods need.
        self.context.append(package)
        
        for obj in package.objects:
            self.read(obj)
        
        self.context.pop()
    
    def process(self, objects):
    
        for obj in objects:
        
            # Do not visit certain types of object if they are undocumented.
            if not self.is_documented(obj):
                continue
            
            handler = Index.Handlers.get(obj.__class__)
            if handler:
                handler(self, obj)
    
    def add_ref(self, obj):
    
        try:
            self.refs.setdefault(obj.name, {})
            if self.context:
                parent = self.context[-1]
            else:
                parent = None
        
        except AttributeError:
            pass
        
        self.refs[obj.name][parent] = self.context[:] + [obj]
    
    def process_body(self, obj):
    
        self.context.append(obj)
        self.process(obj.body)
        self.context.pop()
    
    def handleModule(self, obj):
    
        obj.name = self.name
        self.add_ref(obj)
        self.process_body(obj)
    
    def handleClassDef(self, obj):
    
        self.add_ref(obj)
        self.process_body(obj)
    
    def handleFunctionDef(self, obj):
    
        self.add_ref(obj)
        self.process_body(obj)
    
    Handlers = {ast.Module: handleModule,
                ast.ClassDef: handleClassDef,
                ast.FunctionDef: handleFunctionDef}


class Writer:

    """Writes the structure and documentation of Python source code to an
    HTML file.
    """
    
    Order = {ast.Module: [(ast.ClassDef, "Classes"),
                          (ast.FunctionDef, "Functions")],
             ast.ClassDef: [(ast.FunctionDef, "Methods")]}
    
    CheckDocstring = set([ast.Module, ast.ClassDef, ast.FunctionDef])
    
    Module_Template = (
        "<head>\n"
        "<title>%(title)s</title>\n"
        '<style type="text/css">\n'
        "  .doc { text-align: justify }\n"
        "  .class { border-left: solid 4px #c0e0ff;\n"
        "           border-right: solid 4px #c0e0ff;\n"
        "           border-bottom: solid 4px #c0e0ff;\n"
        "           background-color: #f7f7f7;\n"
        "           padding-left: 8px;\n"
        "           padding-right: 8px;\n"
        "           padding-bottom: 8px }\n"
        "  .class-heading { background-color: #c0e0ff;\n"
        "                   padding: 2px;\n"
        "                   padding-left: 0.25em;\n"
        "                   margin-left: -8px;\n"
        "                   margin-right: -8px }\n"
        "  .function { border-left: solid 4px #d0e0f0;\n"
        "              border-right: solid 4px #d0e0f0;\n"
        "              border-bottom: solid 4px #d0e0f0;\n"
        "              padding-left: 8px;\n"
        "              padding-right: 8px }\n"
        "  .function-heading { font-family: monospace;\n"
        "                      background-color: #d0e0f0;\n"
        "                      padding: 2px;\n"
        "                      padding-left: 0.25em;\n"
        "                      margin-left: -8px;\n"
        "                      margin-right: -8px }\n"
        "</style>\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=%(encoding)s" />\n'
        "</head>\n\n"
        )
    
    def __init__(self, index, output_dir, encoding = "utf8"):
    
        self.index = index
        self.output_dir = output_dir
        self.encoding = encoding
        
        # Keep track of which HTML elements have been started.
        self.elements = []
        
        # Maintain a context stack to allow references to be as close as
        # possible to the context in which they are used.
        self.context = []
    
    def open(self, name):
    
        self.name = name
        output_path = os.path.join(self.output_dir, name + ".html")
        print "Writing", output_path
        self.f = open(output_path, "wb")
        
        self.begin("html", "\n")
        
        self.f.write(Writer.Module_Template % {"title": self.h(name),
                                               "encoding": self.encoding})
        self.begin("body", "\n")
    
    def close(self):
    
        self.end("body", "\n")
        self.end("html")
        self.f.close()
    
    def begin(self, element, spacing = "", attributes = {}):
    
        self.f.write("<" + element)
        if attributes:
            self.w(" ")
        for name, value in attributes.items():
            self.w(name + '="' + str(value) + '" ')
        self.f.write(">")
        self.f.write(spacing)
        
        end_element = element.split()[0]
        self.elements.append(end_element)
        return end_element
    
    def end(self, element = None, spacing = ""):
    
        previous = self.elements.pop()
        if element and element != previous:
            sys.stderr.write("Internal error: cannot close %s element with %s.\n" % (previous, element))
            sys.exit(1)
        
        self.f.write("</" + previous + ">")
        self.f.write(spacing)
    
    def h(self, text):
    
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return text.encode(self.encoding)
    
    def w(self, text):
    
        self.f.write(self.h(text))
    
    def create_ref(self, obj):
    
        """Returns the internal reference for the object specified by obj."""
        
        pieces = self.index.refs[obj.name][self.context[-1]]
        
        return self.encode_ref(pieces)[1]
    
    def get_ref(self, name):
    
        try:
            candidates = self.index.refs[name]
        except KeyError:
            return ""
        
        if len(candidates) == 1:
            ref = candidates.values()[0]
        else:
            # Find the match in the closest context to this one.
            for level in self.context[::-1]:
                try:
                    ref = candidates[level]
                    break
                except KeyError:
                    pass
            else:
                return ""
        
        href, ref = self.encode_ref(ref)
        if href:
            if ref:
                return href + ".html#" + ref
            else:
                return href + ".html"
        else:
            return "#" + ref
    
    def encode_ref(self, pieces):
    
        path = []
        ref = []
        
        for piece in pieces:
            if isinstance(piece, Package) or isinstance(piece, ast.Module):
                path.append(piece.name)
            else:
                ref.append(piece.name)
        
        return ".".join(path), "-".join(ref)
    
    def is_documented(self, obj):
    
        if obj.__class__ in Writer.CheckDocstring:
            return ast.get_docstring(obj)
        else:
            return True
    
    def write(self, obj):
    
        if isinstance(obj, Module):
            self.write_module(obj)
        elif isinstance(obj, Package):
            self.write_package(obj)
    
    def write_module(self, module):
    
        if self.context:
            parent = self.context[-1]
        else:
            parent = None
        
        # Return if the matched object belonging to the parent of this module
        # is not the same as the module object itself, or if no suitable object
        # could be found.
        try:
            match = self.index.refs[module.name][parent][-1]
            if match != module.objects[0]:
                return
        except KeyError:
            return
        
        name = ".".join(filter(lambda y: y != "", map(lambda x: x.name, self.context + [module])))
        self.open(name)
        self.write_objects(module.objects)
        self.close()
    
    def write_package(self, package):
    
        self.context.append(package)
        
        for obj in package.objects:
            self.write(obj)
        
        self.context.pop()
    
    def write_objects(self, objects):
    
        for obj in objects:
        
            # Do not visit certain types of object if they are undocumented.
            if not self.is_documented(obj):
                continue
            
            handler = Writer.Handlers.get(obj.__class__)
            if handler:
                handler(self, obj)
    
    def write_docstring(self, obj, names = set()):
    
        doc = ast.get_docstring(obj)
        if doc:
            lines = map(lambda line: line.rstrip(), doc.split("\n"))
            paragraphs = []
            para = []
            
            for line in lines:
                if line:
                    para.append(line)
                else:
                    paragraphs.append(" ".join(para))
                    para = []
            
            if para:
                paragraphs.append(" ".join(para))
            
            for para in paragraphs:
            
                self.begin('p', attributes = {"class": "doc"}, spacing = "\n")
                
                words = para.split()
                for i in range(len(words)):
                
                    piece = words[i]
                    
                    # Match argument names, if specified.
                    # Remove trailing punctuation.
                    word = piece.rstrip(",.;:()")
                    
                    if word in names:
                        start = piece.index(word)
                        self.w(piece[:start])
                        self.begin("em")
                        self.w(word)
                        self.end("em")
                        self.w(piece[start + len(word):])
                    
                    elif word in self.index.refs and word != obj.name:
                    
                        # Match tokens in the index.
                        ref = self.get_ref(word)
                        
                        if ref:
                            self.begin("a", attributes = {"href": ref})
                            self.w(piece)
                            self.end("a")
                        else:
                            self.w(piece)
                    else:
                        # Just write the word as plain text.
                        self.w(piece)
                    
                    # Add spaces between the words.
                    if i < len(words) - 1:
                        self.w(" ")
                
                self.end("p", spacing = "\n\n")
    
    def write_body(self, obj, heading, show_others = False):
    
        # Add the object to the context.
        if hasattr(obj, "name"):
            self.context.append(obj)
        
        # Collect top-level objects into separate groups.
        objects = {}
        
        for child in obj.body:
            if self.is_documented(child):
                objects.setdefault(child.__class__, []).append(child)
        
        # Write a section for each group in the intended order.
        for type, category in Writer.Order[obj.__class__]:
        
            if type in objects:
            
                end_heading = self.begin(heading)
                self.w(category)
                self.end(end_heading, "\n\n")
                
                self.write_objects(objects[type])
                # Remove the objects from the dictionary.
                del objects[type]
        
        # If categories remain then group them all under a single section.
        if objects and show_others:
            end_heading = self.begin(heading)
            self.w("Other objects")
            self.end(end_heading, "\n\n")
            
            remaining = objects.values()
            remaining.sort()
            
            for objects in remaining:
                self.write_objects(objects)
        
        # Remove the object from the context.
        if hasattr(obj, "name"):
            self.context.pop()
    
    def handleModule(self, obj):
    
        self.begin("h1")
        self.w(self.name)
        self.end("h1", "\n\n")
        
        self.write_docstring(obj)
        
        self.write_body(obj, "h2")
    
    def handleImport(self, obj):
    
        self.begin("p")
        for name in obj.names:
            self.w(name.name)
            if name != obj.names[-1]:
                self.w(", ")
        self.end("p", "\n\n")
    
    def handleClassDef(self, obj):
    
        self.begin('div', attributes = {"class": "class"})
        self.begin("h3", attributes = {"id": self.create_ref(obj),
                                       "class": "class-heading"})
        self.w(obj.name)
        
        if obj.bases:
        
            bases = []
            for base in obj.bases:
                ref = self.get_ref(base.id)
                if ref:
                    bases.append((base.id, ref))
            
            if bases:
                self.w("(")
                for name, ref in bases:
                    self.begin("a", attributes = {"href": ref})
                    self.w(name)
                    self.end("a")
                    
                    if ref != bases[-1][1]:
                        self.w(", ")
                
                self.w(")")
        self.end("h3", "\n\n")
        
        self.write_docstring(obj)
        
        self.write_body(obj, 'h3')
        self.end("div", "\n\n")
    
    def handleFunctionDef(self, obj):
    
        self.begin('div class="function"')
        self.begin("h3", attributes = {"id": self.create_ref(obj),
                                       "class": "function-heading"})
        self.w(obj.name)
        self.w("(")
        
        arg_names = set()
        
        default_start = len(obj.args.args) - len(obj.args.defaults)
        for i in range(len(obj.args.args)):
        
            name = obj.args.args[i]
            self.w(name.id)
            arg_names.add(name.id)
            
            if i >= default_start:
                self.w(" = ")
                self.write_objects([obj.args.defaults[i - default_start]])
            if name != obj.args.args[-1]:
                self.w(", ")
        
        self.w(")")
        self.end("h3", "\n\n")
        
        self.write_docstring(obj, arg_names)
        
        self.write_objects(obj.body)
        self.end("div", "\n\n")
    
    def handleNum(self, obj):
    
        self.w(str(obj.n))
    
    def handleStr(self, obj):
    
        self.w(repr(obj.s))
    
    def handleName(self, obj):
    
        self.w(str(obj.id))
    
    def handleAttribute(self, obj):
    
        self.write_objects([obj.value])

    def handleCall(self, obj):
    
        # Currently only writes the representation of the callable itself
        # and any non-keyword arguments.
        self.write_objects([obj.func])
        self.w("(")
        self.write_objects(obj.args)
        self.w(")")
    
    Handlers = {ast.Attribute: handleAttribute,
                ast.Call: handleCall,   # Call is found in default arguments
                ast.ClassDef: handleClassDef,
                ast.FunctionDef: handleFunctionDef,
                ast.Import: handleImport,
                ast.Module: handleModule,
                ast.Name: handleName,
                ast.Num: handleNum,
                ast.Str: handleStr}

def find_modules(paths):

    trees = []
    
    for path in paths:
    
        file_name = os.path.split(path)[1]
        module_name = os.path.splitext(file_name)[0]
        
        if os.path.isdir(path):
            if os.path.exists(os.path.join(path, "__init__.py")):
                print "Reading", path
                trees.append(
                    Package(module_name,
                            find_modules(glob.glob(os.path.join(path, "*.py")))))
        else:
            print "Reading", path
            source = open(path, "rb").read()
            objects = [ast.parse(source, path)]
            trees.append(Module(module_name, objects))
    
    return trees

def process(paths, output_dir):

    # Compile an index of words to help with cross-referencing and parse the
    # modules found on each of the supplied paths.
    index = Index()
    trees = find_modules(paths)
    
    # Read the files, adding objects that can be referenced to the index.
    for obj in trees:
        index.read(obj)
    
    # Create a writer that uses the index for cross-referencing.
    writer = Writer(index, output_dir)
    
    # Use the writer to create documentation for each of the modules found.
    for obj in trees:
        writer.write(obj)


def usage():

    sys.stderr.write("Usage: %s [-o <output directory>] <Python module file or package directory> ...\n" % sys.argv[0])
    sys.exit(1)

if __name__ == "__main__":

    try:
        at = sys.argv.index("-o")
        output_dir = sys.argv[at + 1]
        inputs = sys.argv[at + 2:]
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

    except ValueError:
        output_dir = os.path.abspath(os.curdir)
        inputs = sys.argv[1:]
    except IndexError:
        usage()
    except OSError:
        sys.stderr.write("Failed to create the output directory: %s\n" % output_dir)
        sys.exit(1)
    
    if not inputs:
        usage()
    
    process(inputs, output_dir)
    
    sys.exit()
