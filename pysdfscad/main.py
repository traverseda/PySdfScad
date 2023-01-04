from lark import Lark, v_args
from lark.visitors import Interpreter, visit_children_decor
import lark
from loguru import logger
import pathlib, sys
import ast
from pysdfscad.openscad_builtins import openscad_functions, openscad_operators, openscad_vars, union
from collections import ChainMap
from functools import reduce
import sdf
from sdf.d3 import SDF3
from sdf.d2 import SDF2


logger.remove()
log_format = "<green>{time}</green> - <level>{level}</level> - {extra} - {message}"
logger.add(sys.stderr, format=log_format,colorize=True, backtrace=False, diagnose=True, catch=True)

#We can get general language definitions here: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/The_OpenSCAD_Language#Chapter_1_--_General
# I try to stick to the same terminology as the book, but it's really not a
# direct 1 to 1 translation. For example I can't really have objects that aren't fundamentally function calls,
# which is why I'd have to go out of my way to keep you from storing an object in a variable.

class OperatorScope():
    """Manage scope using with statements
    """
    def __init__(self, parent):
        self.parent = parent
        self.orig_vars = parent.vars
        self.orig_operators = parent.operators
        self.orig_functions = parent.functions

    def __enter__(self):
        self.parent.vars = self.orig_vars.new_child()
        self.parent.operators = self.orig_operators.new_child()
        self.parent.functions = self.orig_functions.new_child()

    def __exit__(self, *args):
        self.parent.vars = self.orig_vars
        self.parent.operators = self.orig_operators
        self.parent.functions = self.orig_functions

from functools import wraps
def logged(func):
    """Adds scad file line number to exceptions
    """
    @logger.catch(reraise=True)
    @wraps(func)
    def with_logging(self, tree, *args, **kwargs):
        meta = tree.meta
#        with logger.contextualize(line = meta.line, column=meta.column):
        return func(self, tree, *args, **kwargs)
    return with_logging

def extract_objects(children):
    """Extract the objects, and only the
    objects, from the list.
    """
    objects_2d=[]
    objects_3d=[]
    for item in children:
        if isinstance(item,SDF2): objects_2d.append(item)
        if isinstance(item,SDF3): objects_3d.append(item)
    if objects_2d and objects_3d:
        #ToDo: print line numbers
        raise Exception(f"Can't mix both 2D and 3D objects at {tree}")
    return objects_2d or objects_3d

class EvalOpenscad(Interpreter):

    def __init__(self,strict=False):
        self.vars = ChainMap(openscad_vars,{})
        self.operators = ChainMap(openscad_operators,{})
        self.functions = ChainMap(openscad_functions,{})
        self.logger = logger

    number = v_args(inline=True)(float)

    @logged
    @visit_children_decor
    def start(self,tree):
        #Combine the top level objects into one.
        objects = extract_objects(tree)
        if objects:
            return reduce(lambda x, y: sdf.union(x,y), objects)
        return None

    @logged
    @v_args(inline=True)
    def ESCAPED_STRING(self,value):
        out = ast.literal.eval(value)
        assert type(out) == str
        return out

    @logged
    def function_def(self,tree):
        """Define a new function from inside the openscad code
        Basically we defer calling the sub tree until we
        call the new function.
        """
        #ToDo: this is not the most tidy, but I suppose it will do...
        function_name = tree.children[0]
        def_args, def_kwargs = self.visit(tree.children[1])
        function_body=tree.children[2]
        def generated_func(context,*args,**kwargs):
            """A function dynamically generated from
            openscad code
            """
            with OperatorScope(context):
                context.vars.update(def_kwargs)
                args = zip(def_args, args)
                context.vars.update(args)
                context.vars.update(kwargs)
                return context.visit(function_body)
        self.functions[function_name]=generated_func
        return None

    @logged
    def module_def(self,tree):
        #Identical to a function def...
        # Probably some clever way to dedupe it.
        function_name = tree.children[0]
        def_args, def_kwargs = self.visit(tree.children[1])
        function_body=tree.children[2]
        def generated_func(context,*args,**kwargs):
            """A function dynamically generated from
            openscad code
            """
            with OperatorScope(context):
                context.vars.update(def_kwargs)
                args = zip(def_args, args)
                context.vars.update(args)
                context.vars.update(kwargs)
                out = extract_objects(context.visit_children(function_body))
                if not out: return
                return reduce(sdf.union, out)

        self.operators[function_name]=generated_func
        return None

    @logged
    @visit_children_decor
    def var(self,tree):
        return self.vars[tree[0].value]

    @logged
    @visit_children_decor
    def ifelse(self,tree):
        if tree[0]:
            return self.visit_children(tree[1])
        elif len(tree)==3:
            return self.visit_children(tree[2])
        return None

    @logged
    @visit_children_decor
    def vector_index(self,tree):
        vector, index = tree
        return vector[int(index)]

    @logged
    @visit_children_decor
    def range(self,tree):
        #ToDo: This works nothing like openscad's implementation
        if len(tree) == 3:
            return range(int(tree[0]),int(tree[2]),int(tree[1]))
        else:
            return range(int(tree[0]),int(tree[1]))

    @logged
    def operator_call(self,tree):
        """Operators change the scope of a variable,
        but they're also essentially functions that operate
        on groups of objects.

        Operators are things like "translate" or "rotate".

        We need to inject the "children" function into the local
        context for operators calls.
        """
        with OperatorScope(self):
            #children = self.visit_children(tree)
            operator = tree.children[0]
            args,kwargs=self.visit(tree.children[1])
            objects = tree.children[2]
            def get_operator_children():
                """Inject children into operator
                """
                out = extract_objects(self.visit_children(objects))
                return out

            self.functions["children_list"]=get_operator_children
            out = self.operators[operator.value](self,*args,**kwargs)

            #print("operator_call",operator,tree.meta.line,tree.meta.column, out )
            return out

    @logged
    @visit_children_decor
    def function_call(self,tree):
        out = self.functions[tree[0].value](self,*tree[1][0],**tree[1][1])
        return out

    @logged
    @visit_children_decor
    def name(self,children):
        return children[0].value

    @logged
    @visit_children_decor
    def arg_def_name(self,children):
        return children

    @logged
    @visit_children_decor
    def combined_args(self, tree):
        """We greatly prefer to hand kwargs and args to
        downstream functions, so this here just injects
        a default empty tuple or dict in if the user didn't
        define both.
        """
        args = ()
        kwargs = {}
        for child in tree:
            if type(child) == dict:
                kwargs = child
            elif type(child) == list:
                args = child
            else:
                atype = type(child)
                raise Exception(f"Unknown argument type {atype}, arguments should be lists, keyword arguments should be dicts.")
        return args, kwargs

    @logged
    @visit_children_decor
    def args_definition(self,tree):
        args = ()
        kwargs = {}
        for child in tree:
            if type(child) == dict:
                kwargs = child
            elif type(child) == list:
                args = child
            else:
                atype = type(child)
                raise Exception(f"Unknown argument type {atype}, arguments should be lists, keyword arguments should be dicts.")
        return args, kwargs

    @logged
    @visit_children_decor
    def add(self, tree):
        return sum(tree)

    @logged
    @visit_children_decor
    def sub(self,tree):
        return tree[0]-tree[1]

    @logged
    @visit_children_decor
    def neg(self, tree):
        return tree[0]*-1

    @logged
    @visit_children_decor
    def mul(self, tree):
        return tree[0]*tree[1]

    @logged
    @visit_children_decor
    def div(self, tree):
        return tree[0]/tree[1]

    @logged
    @visit_children_decor
    def mod(self, tree):
        return tree[0] % tree[1]

    @logged
    @visit_children_decor
    def lt_op(self, tree):
        return tree[0] < tree[1]

    @logged
    @visit_children_decor
    def gt_op(self, tree):
        return tree[0] < tree[1]

    @logged
    @visit_children_decor
    def conditional_op(self, tree):
        return tree[1] if tree[0] else tree[2]

    @logged
    @visit_children_decor
    def inequality(self,tree):
        return tree[0] != tree[1]

    @logged
    @visit_children_decor
    def equality(self,tree):
        return tree[0] == tree[1]

    @logged
    @visit_children_decor
    def exp(self, tree):
        return tree[0]**tree[1]

    @logged
    @visit_children_decor
    def or_op(self, tree):
        """Used as a union on SDF functions
        """
        return tree[0] | tree[1]

    @logged
    @visit_children_decor
    def and_op(self, tree):
        """Used as an intersection on SDF functions
        """
        return tree[0] & tree[1]

    @logged
    @visit_children_decor
    def args(self, tree):
        return tree

    @logged
    @visit_children_decor
    def kwargvalue(self, tree):
        return tree

    @logged
    @visit_children_decor
    def assign_var(self, tree):
        self.vars[tree[0].value]=tree[1]
        return lark.visitors.Discard

    @logged
    @visit_children_decor
    def vector(self, children):
        if not children:
            return []
        return children[0]

    @logged
    def comment(self,tree):
        return lark.visitors.Discard

    @logged
    @visit_children_decor
    def kwargs(self, tree):
        return {k.value:v for k,v in tree}

    @logged
    def block(self,tree):
        return tree

    @logged
    def __default__(self,tree):
        self.logger.warning(f"Unhandled tree node {tree}")
        return super().__default__(tree)

openscad_parser = Lark((pathlib.Path(__file__).parent/"openscad.lark").read_text(), propagate_positions=True)

def main():
    with open(sys.argv[1]) as f:
        tree = openscad_parser.parse(f.read()) 
        interpreter=EvalOpenscad()
        result = interpreter.visit(tree)
        if not result:
            interpreter.logger.info("No top level geometry to render")
        else:
            result.save('test.stl')

if __name__ == '__main__':
    main()

