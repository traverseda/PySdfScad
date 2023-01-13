"""
"Compiles" and openscad source file into a python abstract syntax
tree.

A lot more involved than the previous interpretor, but surprisignly easier
to debug and generally deal with.

This looks a lot my intimidating than it is (I tell myself, as I try to
wrangle with the monstrocity I've writen).

macropy3 has a good introduction on the topic, but since we're only
worried about outputting/generating an AST we can ignore more than half
of it. Mostly I used it for the overview and for its recomened reading.

https://macropy3.readthedocs.io/

Macropy recomends green tree snakes, which is also the main thing
I use as a reference for python's AST nodes.

https://greentreesnakes.readthedocs.io/en/latest/

Basically, work on the lark syntax first, keep track of what nodes
are unhandled, and write a new method to handle that node.

You probably don't need to work on this unless you're implemnting completly
new syntax though.

Note that we're not actually compiling to python, we're compiling to
python bytecode. We use a third-party module to turn that bytecode into
python source code, but it really shouldn't matter if that representation
looks good or is idiomatic.
"""

from lark import Lark, Transformer, v_args, Tree, Token, Discard
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


# @check_ast
@v_args(meta=True, inline=True)
class OpenscadToPy(Transformer):
    def start(self, meta, *args):
        argsnew = self._normalize_block(args)
        #Weirdly I seem to be required to run my imports inside Main, something
        # to do with how python/the-AST is handling global state.
        # Attemps to get around this lead to globals not working...
        
        names = ("ChildContext","module_echo")
        imports = []
        for name in names:
            imports.append(ast.alias(name=name, asname=None, lineno=0, col_offset=0))

        argsnew.insert(
            0,

            ast.ImportFrom(
                module="pysdfscad.openscad_builtins",
                lineno=0,
                col_offset=0,
                names=imports,
                level=0,
            ),
        )

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
            type_ignores=[],
        )

    def _normalize_block(self, expressions):
        """This function pulls a lot of weight, there are a few things we
        need to do when assembling a code block in our AST.

        We wrap top level expressions that don't save any data in an ast.Expr object, which is requires.
        We re order definitions, so that definitions always appear before the following code.
        We yield from modules.
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

                if False:  # arg.func.id.startswith("module_"):
                    module_definition.append(arg)
                else:
                    function_definition.append(arg)
            else:
                new_expression.append(arg)
        return [*function_definition, *module_definition, *new_expression]

    def operator_call(self, meta, f_name: Token, args, block):
        block_children = self._normalize_block(block)
        if not block_children:

            block_children = [
                ast.Return(value=None, lineno=meta.line, col_offset=meta.column),
                ast.Expr(
                    # We need to do some weirdness with having a reuturn followed by a yield, let python get
                    # confused about whether this function is a generator or not.
                    value=ast.Yield(
                        value=None, lineno=meta.line, col_offset=meta.column
                    ),
                    lineno=meta.line,
                    col_offset=meta.column,
                ),
            ]

        args, kwargs = args

        if f_name.value == "children":
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

        body = [
            ast.FunctionDef(
                name="module_children",
                decorator_list=[],
                body=block_children,
                args=ast.arguments(
                    args=[],
                    posonlyargs=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                lineno=meta.line,
                col_offset=meta.column,
            ),
            ast.Call(
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
            ),
        ]
        body = self._normalize_block(body)
        # children_arg=ast.arg()
        return ast.With(
            items=[
                ast.withitem(
                    context_expr=ast.Call(
                        ast.Name(
                            id="ChildContext",
                            ctx=ast.Load(),
                            lineno=meta.line,
                            col_offset=meta.column,
                        ),
                        args=[],
                        keywords=[],
                        lineno=meta.line,
                        col_offset=meta.column,
                    ),
                    lineno=meta.line,
                    col_offset=meta.column,
                ),
            ],
            body=body,
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
        print("kw_args",args,kwargs)
        return args, kwargs

    def kwargs(self, meta, *children):
        return children

    def args(self, meta, *children):
        return children

    def ESCAPED_STRING(self,token):
        return ast.Constant(
            token.value, None, lineno=token.line, col_offset=token.column
        )


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
        return children

    def module_def(self, meta, name, args, body):
        args, kwargs = args
        for kwarg in kwargs:
            args.append(
                ast.arg(kwarg.arg, lineno=kwarg.lineno, col_offset=kwarg.col_offset)
            )

        defaults = [i.value for i in kwargs]
        body = self._normalize_block(body)
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
        print("Undandled",data,children,meta)
        logger.warning(f"unhandled parse {data}, {children}, {meta}")
        return Discard
        return Tree(data, children, meta)


parser = Lark.open("openscad.lark", rel_to=__file__, propagate_positions=True)

example_text = """
foo=1;
echo("foo");
"""

from loguru import logger  # type: ignore
from meta.asttools import print_ast


@logger.catch
def main():
    import astor  # type: ignore
    import astpretty

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
    scad_locals = {}
    scad_globals = {}
    eval(
        compile(
            result,
            filename="<ast>",
            mode="exec",
        ),
        scad_globals,
        scad_locals,
    )
    print(scad_locals["main"]())
    print(*scad_locals["main"]())


main()
