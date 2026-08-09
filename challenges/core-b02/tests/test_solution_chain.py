from backend.tests.challenge_solvers.solve_core_b02 import solve


def test_solver_chain(base_url):
    assert solve(base_url).startswith("flag{")
