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
