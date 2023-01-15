"""
"Compiles" and openscad source file into a python abstract syntax
tree.

A lot more involved than the previous interpretor, but surprisignly easier
to debug and generally deal with.

This looks a lot my intimidating than it is (I tell myself, as I try to
wrangle with the monstrocity I've writen).

Since AST trees are really annoying to look at and work on we're formatting
this file using `black`. I'm generally not a fan of auto format like
this but I'll be damned if I'm going do manually format all these crazy
AST constructors.

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
python bytecode (more or less).
We use a third-party module to turn that bytecode into
python source code, but it really shouldn't matter if that representation
looks good or is idiomatic.
"""

from lark import Lark, Transformer, v_args, Tree, Token, Discard
import types
import ast
import itertools
from meta.asttools import print_ast  # type: ignore
from pathlib import Path
import functools
import astor


def check_ast(cls):
    # Hack to let us find out when/where we've forgotten a line number
    # or maybe other AST errors in the future
    def decorator(func):
        import astpretty  # type: ignore

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if isinstance(result, ast.AST):
                # print(astor.to_source(result, add_line_information=True))
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


@check_ast
@v_args(meta=True, inline=True)
class OpenscadToPy(Transformer):
    def start(self, meta, *args):
        argsnew = list(self._normalize_block(args))

        return ast.Module(
            [
                ast.ImportFrom(
                    module="pysdfscad.openscad_builtins",
                    lineno=0,
                    col_offset=0,
                    names=[
                        ast.alias(name="*", asname=None, lineno=0, col_offset=0),
                    ],
                    level=0,
                ),
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
        #logger.opt(depth=1).info(f"{expressions}")
        for arg in expressions:
            if isinstance(arg, types.GeneratorType):
                yield from self._normalize_block(arg)

            elif isinstance(arg, ast.Call):
                # Wrap modules in a yield from, so we can unwind our openscad tree into one
                # top level piece of geometry.
                if arg.func.func.id.startswith("module_"):
                    new_expression.append(
                        ast.Expr(
                            ast.YieldFrom(
                                arg, lineno=arg.lineno, col_offset=arg.col_offset
                            ),
                            lineno=arg.lineno,
                            col_offset=arg.col_offset,
                        )
                    )
                # "When an expression, such as a function call, appears as a statement by itself (an expression statement), with its return value not used or stored, it is wrapped in this container."
                # So we need to wrap lone calls that are just hanging out on a line in an Expr
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
        yield from [*function_definition, *module_definition, *new_expression]

    def operator_call(self, meta, f_name: Token, args, block):
        block_children = list(self._normalize_block(block))

        args, kwargs = args

        if f_name.value == "children":
            yield ast.Expr(
                value=ast.YieldFrom(
                    ast.Call(
                        ast.Name(
                            id="children",
                            ctx=ast.Load(),
                            lineno=f_name.line,
                            col_offset=f_name.column,
                        ),
                        args=[*args],
                        keywords=list(kwargs),
                        lineno=meta.line,
                        col_offset=meta.column,
                    ),
                    lineno=meta.line,
                    col_offset=meta.column,
                ),
                lineno=meta.line,
                col_offset=meta.column,
            )
            return
        call_child = []
        if block_children:
            yield ast.FunctionDef(
                name="children",
                decorator_list=[],
                body=block_children,
                args=ast.arguments(
                    args=[],
                    posonlyargs=[],
                    kwonlyargs=[],
                    # kwarg=ast.arg(arg='kwargs', annotation=None, type_comment=None,
                    #                lineno=meta.line,
                    #                col_offset=meta.column,
                    # ),
                    kw_defaults=[],
                    defaults=[],
                ),
                lineno=meta.line,
                col_offset=meta.column,
            )
            call_child = [
                ast.Name(
                    id="children",
                    ctx=ast.Load(),
                    lineno=f_name.line,
                    col_offset=f_name.column,
                ),
            ]

        body = [
            ast.Call(
                func=ast.Call(
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
                args=call_child,
                keywords=[],
                lineno=meta.line,
                col_offset=meta.column,
            )
        ]
        body = list(
            self._normalize_block(
                body,
            )
        )
        yield from body

    #        yield ast.Delete(
    #            targets=[
    #                ast.Name(
    #                    id="children",
    #                    ctx=ast.Del(),
    #                    lineno=meta.line,
    #                    col_offset=meta.column,
    #                ),
    #            ],
    #            lineno=meta.line,
    #            col_offset=meta.column,
    #        )

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

    def combined_args(self, meta, *args_orig):
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
        return args, kwargs

    def for_loop(self, meta, args, block):
        args, kwargs = args
        block = list(self._normalize_block(block))
        assert not args
        target = []
        values = []
        for keyword in kwargs:
            target.append(
                ast.Name(
                    id=keyword.arg,
                    ctx=ast.Store(),
                    lineno=meta.line,
                    col_offset=meta.column,
                )
            )
            values.append(keyword.value)
        if len(target) > 1:
            target = ast.Tuple(
                target, ast.Store(), lineno=meta.line, col_offset=meta.column
            )
        else:
            target = target[0]
        if len(values) > 1:
            values= ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(
                            id="itertools",
                            ctx=ast.Load(),
                            lineno=meta.line,
                            col_offset=meta.column,
                        ),
                        attr="product",
                        ctx=ast.Load(),
                        lineno=meta.line,
                        col_offset=meta.column,
                    ),
                    args=values,
                    keywords=[],
                    lineno=meta.line,
                    col_offset=meta.column,
                    body=block,
                )
        else:
            values = values[0]
        result = ast.For(
            target=target,
            iter=values,
            body=block,
            orelse=[],
            lineno=meta.line,
            col_offset=meta.column,
        )
        yield result
        print("=======for_ast========")
        print(astor.dump_tree(result, indentation="| "))

    def kwargs(self, meta, *children):
        return children

    def args(self, meta, *children):
        return children

    def ESCAPED_STRING(self, token):
        return ast.Constant(
            token.value, None, lineno=token.line, col_offset=token.column
        )

    def number(self, meta, token):
        return ast.Constant(
            float(token.value), None, lineno=meta.line, col_offset=meta.column
        )

    def var(self, meta, token):
        return ast.Name(
            id="var_" + token.value,
            ctx=ast.Load(),
            lineno=token.line,
            col_offset=token.column,
        )

    def kwargvalue(self, meta, token, value):
        return ast.keyword(
            arg="var_" + token.value,
            value=value,
            lineno=token.line,
            col_offset=token.column,
        )

    def assign_var(self, meta, name, value):
        yield ast.Assign(
            targets=[
                ast.Name(
                    id="var_" + name.value,
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
                ast.arg(arg="var_" + arg.value, lineno=arg.line, col_offset=arg.column)
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
        body = list(self._normalize_block(body))
        yield ast.FunctionDef(
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
        yield ast.FunctionDef(
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

    def vector(self, meta, args):
        return ast.List(
            list(args),
            ctx=ast.Load(),
            lineno=meta.line,
            col_offset=meta.column,
        )

    @v_args(meta=False, inline=False)
    def __default__(self, data, children, meta):
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

    example_py = """
for x,y in itertools.product(((1,2))):
    pass
def children(**kwargs):
    setlocals(kwargs)
"""
    if example_py:
        print("====Python AST=====")
        result = ast.parse(example_py)
        print(astor.dump_tree(result, indentation="| "))
        print("-------------------")

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
    exec(
        compile(
            result,
            filename="<ast>",
            mode="exec",
        ),
        scad_locals,
    )
    print(scad_locals["main"]())
    print(*scad_locals["main"]())


if __name__ == "__main__":
    main()
