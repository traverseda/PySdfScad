from pysdfscad.main import EvalOpenscad, openscad_parser
import logging
import pytest
from _pytest.logging import caplog as _caplog
from loguru import logger

@pytest.fixture
def caplog(_caplog):
    """Fix caplog to work with loguru
    """
    class PropogateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropogateHandler(), format="{message}")
    yield _caplog
    logger.remove(handler_id)

def eval_scad(data):
    tree = openscad_parser.parse(data)
    interpretor = EvalOpenscad()
    return interpretor.visit(tree)

def test_echo(caplog):
    eval_scad("""
    echo("Hello World");
    """)    
    assert 'ECHO: "Hello World"' in caplog.text

def test_basic_types(caplog):
    eval_scad("""
    echo(
        vector=[1,2, 3],
        number=1,
        undef=undef,
        true=true,
        false=false,
        string="Hello"
    );
    """)
    expected = 'ECHO: '\
        'vector=[1.0, 2.0, 3.0], '\
        'number=1.0, '\
        'undef=None, '\
        'true=True, '\
        'false=False, '\
        'string="Hello"'\
        "\n"

    assert expected in caplog.text

def test_basic_math(caplog):
    eval_scad("""
    echo(
        add=1+1,
        sub=1-2,
        mod=7%2,
        exp=10^2,
        div=10/2,
        mul=1*4
    );
    """)
    expected = 'ECHO: '\
        'add=2.0, '\
        'sub=-1.0, '\
        'mod=1.0, '\
        'exp=100.0, '\
        'div=5.0, '\
        'mul=4.0'\
        "\n"
    assert expected in caplog.text

def test_set_variable(caplog):
    eval_scad("""
    foo= 1+1;
    echo(foo);
    """)
    assert "ECHO: 2" in caplog.text

def test_def_function(caplog):
    eval_scad("""
    function func1(r)=r;
    echo(func1(2));
    """)    
    assert 'ECHO: 2' in caplog.text

def test_range(caplog):
    eval_scad("""
    echo([0:2:20]);
    """)    
    assert 'ECHO: range(0, 20, 2)\n' in caplog.text

def test_for(caplog):
    out = eval_scad("for (x=[1,2,3],y=[1,2,3])echo(x,y);")
    expected=["ECHO: 1.0, 1.0",
              "ECHO: 1.0, 2.0",
              "ECHO: 1.0, 3.0",
              "ECHO: 2.0, 1.0",
              "ECHO: 2.0, 2.0",
              "ECHO: 2.0, 3.0",
              "ECHO: 3.0, 1.0",
              "ECHO: 3.0, 2.0",
              "ECHO: 3.0, 3.0"]
    for expected, line in zip(expected, caplog.text.split("\n")):
        assert expected in line

def test_def_function_nested(caplog):
    eval_scad("""
    function func1(r)=r;
    echo(1+func1(1));
    """)    
    assert 'ECHO: 2' in caplog.text

#def test_sphere():
#    out = eval_scad("sphere(r=20);")
#    out = out.generate(samples=2**22)
#    print(hash(tuple(out)))
#    raise

def test_scope(caplog):
    """Test to make sure blocks are properly
    maintaining scope
    """
    eval_scad("""
    foo=3;
    union(){
        foo=14;
        echo(foo);
    }
    echo(foo);
    """)
    loglines = caplog.text.split("\n")
    assert "ECHO: 14" in loglines[0]
    assert "ECHO: 3" in loglines[1]

