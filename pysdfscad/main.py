from lark import Lark, v_args
from lark.visitors import Interpreter
from loguru import logger
import pathlib, sys
import ast
from pysdfscad.openscad_builtins import openscad_builtins
from  collections import ChainMap


@v_args(inline=True)
class EvalOpenscad(Interpreter):
    from operator import add, sub, mul, truediv as div, neg
    number = float
    def __init__(self):
        self.vars = {}
        self.functions = ChainMap(openscad_builtins,{})
        self.logger = logger

    def assign_var(self, name, value):
        self.vars[name] = value

    def kwargs(self,*kwargtokens):
        """Convert kwargs into dictionary
        """
        return {k:v for k,v in kwargtokens}

    def function_call(self,name,args):
        args, kwargs = args
        return self.functions[name](*args,**kwargs)

    def COMMENT(self,comment):
        return

    def var(self, name):
        try:
            return self.vars[name]
        except KeyError:
            raise Exception("Variable not found: %s" % name)

    #Misc cleanup

    def combined_args(self,*args):
        """We want to always have args and kwargs,
        but the parser will drop them if they don't exist.
        """
        if len(args)==2:
            return args

        new_args=()
        new_kwargs={}
        if len(args)==1:
            if type(args[0])==dict:
                new_kwargs=args[0]
            elif type(args[0])==tuple:
                new_args=args[0]

        return new_args, new_kwargs

    def args(self, *args):
        return args
    def kwargvalue(self, *args):
        return args
    NAME=str
    def ESCAPED_STRING(self,value):
        #Warning, this is a safe eval but... it can return non string objects if the string
        # isn't qouted properly.
        out = ast.literal_eval(value)
        assert type(out) == str
        return out

openscad_parser = Lark((pathlib.Path(__file__).parent/"openscad.lark").read_text(), )

if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        tree = openscad_parser.parse(f.read()) 
#        print(tree)
        transformer=EvalOpenscad()
        result = transformer.transform(tree)
        print(result)
        print(transformer.vars)




