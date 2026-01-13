from pyiwsl import hello

def test_hello():
    assert hello("pyiwsl") == "hello, pyiwsl"

test_hello()