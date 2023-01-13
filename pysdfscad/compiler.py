"""
"Compiles" and openscad source file into a python abstract syntax
tree.

A lot more involved than the previous interpretor, but surprisignly easier
to debug and generally deal with.
"""

from lark import Lark, Transformer, v_args, ast_utils, Tree, Token
import ast
from meta.asttools import print_ast  # type: ignore
from pathlib import Path
import functools


def check_ast(cls):
    # Hack to let us find out when/where we've forgotten a line number
    # or maybe other AST errors in the future
    def decorator(func):
        import astpretty  # type: ignore

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if isinstance(result, ast.AST):
                try:
                    astpretty.pformat(result, indent="| ")
                except Exception as e:
                    if type(e) in (AttributeError,):
                        raise e
                # Validate the ast...
                pass
            return result

        return wrapper

    for attr in cls.__dict__:  # there's propably a better way to do this
        if callable(getattr(cls, attr)):
            setattr(cls, attr, decorator(getattr(cls, attr)))
    return cls


#@check_ast
@v_args(meta=True, inline=True)
class OpenscadToPy(Transformer):

    def start(self, meta, *args):
        argsnew = self._normalize_block(args)

        return ast.Module(
            [
                ast.FunctionDef(
                    name="main",
                    decorator_list=[],
                    body=argsnew,
                    args=ast.arguments(
                        args=[],
                        posonlyargs=[],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    lineno=0,
                    col_offset=0,
                ),
            ],
        )

    def _normalize_block(self, expressions):
        """This function pulls a lot of weight, there are a few things we
        need to do when assembling a code block in our AST.

        We wrap top level expressions that don't save any data in an ast.Expr object, which is requires.
        We re order definitions, so that functions get defined before modules, avoiding namespace collisions.
        """
        new_expression = []
        module_definition = []
        function_definition = []
        for arg in expressions:
            if isinstance(arg, ast.Call):
                # "When an expression, such as a function call, appears as a statement by itself (an expression statement), with its return value not used or stored, it is wrapped in this container."
                # So we need to wrap lone calls that are just hanging out on a line in an Expr
                if arg.func.id.startswith("module_"):
                    new_expression.append(
                        ast.Expr(
                            ast.YieldFrom(
                                arg, lineno=arg.lineno, col_offset=arg.col_offset
                            ),
                            lineno=arg.lineno,
                            col_offset=arg.col_offset,
                        )
                    )
                else:
                    new_expression.append(
                        ast.Expr(
                            value=arg, lineno=arg.lineno, col_offset=arg.col_offset
                        )
                    )
            elif isinstance(arg, ast.FunctionDef):
                if arg.func.id.startswith("module_"):
                    module_definition.append(arg)
                else:
                    function_definition.append(arg)
            else:
                expnew.append(arg)
        return [*function_definition, *module_definition, *new_expression]

    def operator_call(self, meta, f_name: Token, args, block):
        block_children = self._normalize_block(block)

        args, kwargs = args
        # children_arg=ast.arg()
        return ast.Call(
            ast.Name(
                id="module_" + f_name.value,
                ctx=ast.Load(),
                lineno=f_name.line,
                col_offset=f_name.column,
            ),
            args=[*args],
            keywords=list(kwargs),
            lineno=meta.line,
            col_offset=meta.column,
        )

    def function_call(self, meta, f_name: Token, args):
        args, kwargs = args
        return ast.Call(
            ast.Name(
                id="function_" + f_name.value,
                ctx=ast.Load(),
                lineno=f_name.line,
                col_offset=f_name.column,
            ),
            args=list(args),
            keywords=list(kwargs),
            lineno=meta.line,
            col_offset=meta.column,
        )

    def combined_args(self, meta, args=list(), kwargs=dict()):
        return args, kwargs

    def kwargs(self, meta, *children):
        return children

    def args(self, meta, *children):
        return children

    def number(self, meta, token):
        return ast.Constant(
            int(token.value), None, lineno=meta.line, col_offset=meta.column
        )

    def var(self, meta, token):
        return ast.Name(
            id=token.value, ctx=ast.Load(), lineno=token.line, col_offset=token.column
        )

    def kwargvalue(self, meta, token, value):
        return ast.keyword(
            arg=token.value, value=value, lineno=token.line, col_offset=token.column
        )

    def assign_var(self, meta, name, value):
        return ast.Assign(
            targets=[
                ast.Name(
                    id=name.value,
                    ctx=ast.Store(),
                    lineno=name.line,
                    col_offset=name.column,
                ),
            ],
            value=value,
            lineno=meta.line,
            col_offset=meta.column,
        )

    def args_definition(self, meta, *args_orig):
        if len(args_orig) == 2:
            args, kwargs = args_orig
        elif len(args_orig) == 1:
            print("args_definition", args_orig)
            if isinstance(args_orig[0][0], ast.keyword):
                args = []
                kwargs = args_orig[0]
            else:
                args = args_orig[0]
                kwargs = []
        elif len(args_orig) == 0:
            args = []
            kwargs = []
        else:
            raise Exception(
                "That's the wrong nuber of args, something has gone very wrong"
            )

        newargs = []
        for arg in args:
            newargs.append(
                ast.arg(arg=arg.value, lineno=arg.line, col_offset=arg.column)
            )
        return newargs, kwargs

    def arg_def_name(self, meta, *children):
        return children

    def name(self, meta, children):
        return children

    def add(self, meta, left, right):
        return ast.BinOp(
            left=left,
            right=right,
            op=ast.Add(),
            lineno=meta.line,
            col_offset=meta.column,
        )

    def block(self, meta, *children):
        print("block", children)
        return children

    def module_def(self, meta, name, args, body):
        args, kwargs = args
        for kwarg in kwargs:
            args.append(
                ast.arg(kwarg.arg, lineno=kwarg.lineno, col_offset=kwarg.col_offset)
            )

        defaults = [i.value for i in kwargs]
        body = self._normalize_block(body) or [
            ast.Pass(lineno=meta.line, col_offset=meta.column),
        ]
        return ast.FunctionDef(
            name="module_" + name.value,
            decorator_list=[],
            body=body,
            args=ast.arguments(
                args=args,
                posonlyargs=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=defaults,
            ),
            lineno=meta.line,
            col_offset=meta.column,
        )

    def function_def(self, meta, name, args, body):
        args, kwargs = args
        for kwarg in kwargs:
            args.append(
                ast.arg(kwarg.arg, lineno=kwarg.lineno, col_offset=kwarg.col_offset)
            )

        defaults = [i.value for i in kwargs]
        #        print("kwargs",kwargs)
        return ast.FunctionDef(
            name="function_" + name.value,
            decorator_list=[],
            body=[
                ast.Return(
                    value=body,
                    lineno=meta.line,
                    col_offset=meta.column,
                )
            ],
            args=ast.arguments(
                args=args,
                posonlyargs=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=defaults,
            ),
            lineno=meta.line,
            col_offset=meta.column,
        )

    @v_args(meta=False, inline=False)
    def __default__(self, data, children, meta):
        print("unhandled", data, children, meta)
        return Tree(data, children, meta)


parser = Lark.open("openscad.lark", rel_to=__file__, propagate_positions=True)

example_text = """
foo()echo();

module foo(bar=2){}
function foo()=1;
"""

from loguru import logger  # type: ignore
from meta.asttools import print_ast


@logger.catch
def main():
    import astor  # type: ignore
    import astpretty

    py_example = """
    """
    pytree = ast.parse(py_example)
    print("=======pytree=====")
    # print_ast(pytree)
    #    astpretty.pprint(pytree, indent="| ", show_offsets=False)
    print(astor.dump_tree(pytree, indentation="| "))
    print(astor.to_source(pytree))
    print("---------")

    tree = parser.parse(example_text)
    result = OpenscadToPy().transform(tree)
    print("====AST=====")
    print(result)
    print(astor.dump_tree(result, indentation="| "))
    print("=====generated_code=====")

    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import TerminalTrueColorFormatter

    source = astor.to_source(result, add_line_information=True)
    print(highlight(source, PythonLexer(), TerminalTrueColorFormatter()))
    print("-----------")
    print("===Running generated code===")

    import pysdfscad.openscad_builtins  # type: ignore

    def module_to_dict(module):
        return {k: getattr(module, k) for k in dir(module) if not k.startswith("_")}

    openscad_builtins = module_to_dict(pysdfscad.openscad_builtins)
    # Remove python builtins
    openscad_builtins["__builtins__"] = {}

    scad_locals = {}
    eval(
        compile(
            result,
            filename="<ast>",
            mode="exec",
        ),
        openscad_builtins,
        scad_locals,
    )
    print(scad_locals)


main()
