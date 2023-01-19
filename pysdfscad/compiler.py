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
import lark
import types
import ast
import itertools
from pathlib import Path
import functools
import astor

def lines(arg):
    """Convert various lark primitives into python AST compatible line/column metadata.
    """
    if isinstance(arg,lark.tree.Meta):
        return {"lineno":arg.line,"col_offset":arg.column,"end_lineno":arg.end_line,"end_col_offset":arg.end_column}
    if isinstance(arg,lark.lexer.Token):
        return {"lineno":arg.line,"col_offset":arg.column,"end_lineno":arg.end_line,"end_col_offset":arg.end_column}
    elif isinstance(arg, ast.AST):
        return {"lineno":arg.lineno,"col_offset":arg.col_offset,"end_lineno":arg.end_lineno,"end_col_offset":arg.end_col_offset}

    argtype=type(arg)
    raise TypeError(f"Unknown type {argtype} for {arg}")

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
        # logger.opt(depth=1).info(f"{expressions}")
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
                                arg, **lines(arg),
                            ),
                            **lines(arg),
                        )
                    )
                # "When an expression, such as a function call, appears as a statement by itself (an expression statement), with its return value not used or stored, it is wrapped in this container."
                # So we need to wrap lone calls that are just hanging out on a line in an Expr
                else:
                    new_expression.append(
                        ast.Expr(
                            value=arg, **lines(arg),
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

        call_child = []
        if block_children:
            yield ast.FunctionDef(
                name="children_"+f_name.value,
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
                **lines(meta)
            )
            call_child = [
                ast.Name(
                    id="children_"+f_name.value,
                    ctx=ast.Load(),
                    **lines(f_name),
                ),
            ]

        body = [
            ast.Call(
                func=ast.Call(
                    ast.Name(
                        id="module_" + f_name.value,
                        ctx=ast.Load(),
                        **lines(f_name),
                    ),
                    args=[*args],
                    keywords=list(kwargs),
                    **lines(meta)
                ),
                args=call_child,
                keywords=[],
                **lines(meta)
            )
        ]
        body = list(
            self._normalize_block(
                body,
            )
        )
        yield from body

    def COMMENT(self, token):
        return ast.Expr(
            ast.Constant(token.value, **lines(token)),

            **lines(token),
        )

    def function_call(self, meta, f_name: Token, args):
        args, kwargs = args
        return ast.Call(
            ast.Name(
                id="function_" + f_name.value,
                ctx=ast.Load(),
                **lines(f_name),
            ),
            args=list(args),
            keywords=list(kwargs),
            **lines(meta),
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
                    **lines(meta)
                )
            )
            values.append(keyword.value)
        if len(target) > 1:
            target = ast.Tuple(
                target, ast.Store(), **lines(meta),
            )
        else:
            target = target[0]
        if len(values) > 1:
            values = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(
                        id="itertools",
                        ctx=ast.Load(),
                        **lines(meta)
                    ),
                    attr="product",
                    ctx=ast.Load(),
                    **lines(meta)
                ),
                args=values,
                keywords=[],
                **lines(meta),
                body=block,
            )
        else:
            values = values[0]
        result = ast.For(
            target=target,
            iter=values,
            body=block,
            orelse=[],
            **lines(meta)
        )
        yield result
        print("=======for_ast========")
        print(astor.dump_tree(result, indentation="| "))

    def kwargs(self, meta, *children):
        return children

    def args(self, meta, *children):
        return children

    def ESCAPED_STRING(self, token):

        out = ast.literal_eval(token.value)
        assert type(out) == str
        return ast.Constant(out, None, **lines(token),)

    def number(self, meta, token):
        #Convert to int or float depending...
        out = ast.literal_eval(token.value)
        return ast.Constant(
            out, None, **lines(meta)
        )

    def var(self, meta, token):
        return ast.Name(
            id="var_" + token.value,
            ctx=ast.Load(),
            **lines(token)
        )

    def kwargvalue(self, meta, token, value):
        return ast.keyword(
            arg="var_" + token.value,
            value=value,
            **lines(token),
        )

    def assign_var(self, meta, name, value):
        yield ast.Assign(
            targets=[
                ast.Name(
                    id="var_" + name.value,
                    ctx=ast.Store(),
                    **lines(name)
                ),
            ],
            value=value,
            **lines(meta)
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
                ast.arg(arg="var_" + arg.value, **lines(arg))
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
            **lines(meta)
        )

    def mul(self, meta, left, right):
        return ast.BinOp(
            left=left,
            right=right,
            op=ast.Mult(),
            **lines(meta)
        )

    def sub(self, meta, left, right):
        return ast.BinOp(
            left=left,
            right=right,
            op=ast.Sub(),
            **lines(meta)
        )

    def mod(self, meta, left, right):
        return ast.BinOp(
            left=left,
            right=right,
            op=ast.Mod(),
            **lines(meta)
        )

    def exp(self, meta, left, right):
        return ast.BinOp(
            left=left,
            right=right,
            op=ast.Pow(),
            **lines(meta)
        )

    def div(self, meta, left, right):
        return ast.Call(
            ast.Name(
                id="div",
                ctx=ast.Load(),
                **lines(meta)
            ),
            args=[left,right],
            keywords=[],
            **lines(meta)
        )

    def ifelse(self, meta, test, body, orelse=None):
        if orelse:
            orelse = list(self._normalize_block(orelse))
        else:
            orelse = []
        body = list(self._normalize_block(body))
        return ast.If(
            test=test,
            body=body,
            orelse=orelse,
            **lines(meta)
        )

    def inequality(self, meta, left, right):
        return ast.Compare(
            left=left,
            ops=[
                ast.NotEq(),
            ],
            comparators=[
                right,
            ],
            **lines(meta)
        )

    def equality(self, meta, left, right):
        return ast.Compare(
            left=left,
            ops=[
                ast.Eq(),
            ],
            comparators=[
                right,
            ],
            **lines(meta)
        )
    def and_op(self, meta, left, right):
        return ast.BoolOp(
                values=[left,right,],
            op=ast.And(),
            **lines(meta)
        )

    def lt_op(self, meta, left, right):
        return ast.Compare(
            left=left,
            ops=[
                ast.Lt(),
            ],
            comparators=[
                right,
            ],
            **lines(meta)
        )

    def gt_op(self, meta, left, right):
        return ast.Compare(
            left=left,
            ops=[
                ast.Gt(),
            ],
            comparators=[
                right,
            ],
            **lines(meta)
        )

    def vector_index(self, meta, obj,idx):
        return ast.Subscript(obj,idx,
            ctx=ast.Load(),
            **lines(meta)
        )

    def range(self, meta, start, stop, step=None):
        if step != None:
            step, stop = stop, step
        else:
            step = ast.Constant(
                value=1,
                kind=None,
                **lines(meta)
            )
        return ast.Call(
            func=ast.Name(
                id="scad_range",
                ctx=ast.Load(),
                **lines(meta)
            ),
            args=[start, stop, step],
            keywords=[],
            **lines(meta),
        )

    def conditional_op(self, meta, test, body, orelse):
        return ast.IfExp(
            test=test,
            body=body,
            orelse=orelse,
            **lines(meta),
        )

    def neg(self, meta, token):
        return ast.UnaryOp(
            op=ast.USub(),
            operand=token,
            **lines(token),
        )

    def block(self, meta, *children):
        return children

    def module_def(self, meta, name, args, body):
        args, kwargs = args
        for kwarg in kwargs:
            args.append(
                ast.arg(kwarg.arg, **lines(kwarg),)
            )

        

        defaults = [i.value for i in kwargs]
        inner_body = list(self._normalize_block(body))
        inner_defaults =[
                ]
        for arg in args:
            inner_defaults.append(ast.Name(id=arg.arg,
                                           ctx=ast.Load(),
                **lines(meta),

                ))
        inner_defaults.append(ast.Name(id="module_children",
                                       ctx=ast.Load(),
            **lines(meta),

            ))

        body = [
            ast.FunctionDef(
                name=name.value + "_inner",
                decorator_list=[],
                body=inner_body,
                args=ast.arguments(
                    args=[
                        *args,
                        ast.arg("module_children", **lines(meta)),
                        ],
                    posonlyargs=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=inner_defaults,
                ),

                **lines(meta),
            ),
            ast.Return(
                value=ast.Name(
                    name.value + "_inner",
                    ctx=ast.Load(),
                    **lines(meta),
                ),
                **lines(meta),
            ),
        ]
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
            **lines(meta),
        )

    def function_def(self, meta, name, args, body):
        args, kwargs = args
        for kwarg in kwargs:
            args.append(
                ast.arg(kwarg.arg, **lines(kwarg),)
            )

        defaults = [i.value for i in kwargs]
        yield ast.FunctionDef(
            name="function_" + name.value,
            decorator_list=[],
            body=[
                ast.Return(
                    value=body,
                    **lines(meta),
                )
            ],
            args=ast.arguments(
                args=args,
                posonlyargs=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=defaults,
            ),
            **lines(meta),
        )

    def vector(self, meta, args):
        return ast.List(
            list(args),
            ctx=ast.Load(),
            **lines(meta),
        )

    @v_args(meta=False, inline=False)
    def __default__(self, data, children, meta):
        raise


parser = Lark.open("openscad.lark", rel_to=__file__, propagate_positions=True)
example_text = """
"""


from loguru import logger  # type: ignore


@logger.catch
def main():
    import astor  # type: ignore

    example_py = """
foo = (1+1)/2
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
