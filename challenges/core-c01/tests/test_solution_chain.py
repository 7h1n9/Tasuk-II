from backend.tests.challenge_solvers.solve_core_c01 import solve


def test_solver_chain(base_url):
    assert solve(base_url).startswith("flag{")
