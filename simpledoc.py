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

import ast, os, sys

class Writer:

    """Writes the structure and documentation of Python source code to an
    HTML file.
    """
    
    Order = {ast.Module: [(ast.ClassDef, "Classes"),
                          (ast.FunctionDef, "Functions")],
             ast.ClassDef: [(ast.FunctionDef, "Methods")]}
    
    CheckDocstring = set([ast.ClassDef, ast.FunctionDef])
    
    def __init__(self, f, name, encoding = "utf8"):
    
        self.f = f
        self.name = name
        self.encoding = encoding
        
        # Keep track of which HTML elements have been started.
        self.elements = []
        
        # Compile an index of words to help with cross-referencing.
        self.index = {}
        
        # Maintain a context stack to allow references to be as close as
        # possible to the context in which they are used.
        self.context = []
        
        self.begin("html", "\n")
        
        self.begin("head", "\n")
        self.begin("title")
        self.w(name)
        self.end("title", "\n")
        self.begin('style type="text/css"', "\n")
        self.w(".doc { text-align: justify }\n")
        self.w(".class { border-left: solid 4px #d0d0ff;\n"
               "         background-color: #f7f7f7;\n"
               "         padding-left: 0.5em }\n")
        self.w(".class-heading { background-color: #d0e0ff; padding: 2px }\n")
        self.w(".function { border-left: solid 4px #d0dfff;\n"
               "            padding-left: 0.5em }\n")
        self.w(".function-heading { font-family: monospace }\n")
        self.end(spacing = "\n")
        self.f.write('<meta http-equiv="Content-Type" content="text/html; charset=%s" />\n' % encoding)
        self.end("head", "\n\n")
        
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
            self.w(name + '="' + str(value) + '"')
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
    
        return "-".join(map(lambda x: x.name, self.context + [obj]))
    
    def is_documented(self, obj):
    
        if obj.__class__ in Writer.CheckDocstring:
            return ast.get_docstring(obj)
        else:
            return True
    
    def write(self, objects):
    
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
            self.begin('p class="doc"', "\n")
            
            words = doc.split()
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
                
                elif word in self.index and word != obj.name:
                
                    # Match tokens in the index.
                    candidates = self.index[word]
                    
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
                    
                    if ref:
                        self.begin("a", attributes = {"href": "#" + ref})
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
            objects.setdefault(child.__class__, []).append(child)
            try:
                if self.is_documented(child):
                    self.index.setdefault(child.name, {})
                    self.index[child.name][obj] = self.create_ref(child)
            except AttributeError:
                pass
        
        # Write a section for each group in the intended order.
        for type, category in Writer.Order[obj.__class__]:
        
            if type in objects:
            
                end_heading = self.begin(heading)
                self.w(category)
                self.end(end_heading, "\n\n")
                
                self.write(objects[type])
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
                self.write(objects)
        
        # Remove the object from the context.
        if hasattr(obj, "name"):
            self.context.pop()
    
    def handleModule(self, obj):
    
        self.begin("h1")
        self.w(self.name)
        self.end("h1", "\n\n")
        
        self.index = {}
        self.write_body(obj, "h2")
    
    def handleImport(self, obj):
    
        self.begin("p")
        for name in obj.names:
            self.w(name.name)
            if name != obj.names[-1]:
                self.w(", ")
        self.end("p", "\n\n")
    
    def handleClassDef(self, obj):
    
        self.begin('div class="class"')
        self.begin("h3", attributes = {"id": self.create_ref(obj),
                                       "class": "class-heading"})
        self.w(obj.name)
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
                self.write([obj.args.defaults[i - default_start]])
            if name != obj.args.args[-1]:
                self.w(", ")
        
        self.w(")")
        self.end("h3", "\n\n")
        
        self.write_docstring(obj, arg_names)
        
        self.write(obj.body)
        self.end("div", "\n\n")
    
    def handleNum(self, obj):
    
        self.w(str(obj.n))
    
    def handleStr(self, obj):
    
        self.w(repr(obj.s))
    
    def handleName(self, obj):
    
        self.w(str(obj.id))
    
    def handleAttribute(self, obj):
    
        self.write([obj.value])
    
    Handlers = {ast.Module: handleModule,
                ast.Import: handleImport,
                ast.ClassDef: handleClassDef,
                ast.FunctionDef: handleFunctionDef,
                ast.Num: handleNum,
                ast.Str: handleStr,
                ast.Name: handleName,
                ast.Attribute: handleAttribute}

def process(path):

    source = open(path, "rb").read()
    
    file_name = os.path.split(path)[1]
    output_path = file_name + ".html"
    
    w = Writer(open(output_path, "wb"), os.path.splitext(file_name)[0])
    w.write([ast.parse(source, path)])
    w.close()

if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.stderr.write("Usage: %s <Python file> ...\n" % sys.argv[0])
        sys.exit(1)
    
    for path in sys.argv[1:]:
        process(path)
    
    sys.exit()
