from backend.tests.challenge_solvers.solve_core_b02 import solve


def test_reset_rotates_flag_but_keeps_workflow(base_url, reset_instance):
    old_flag = solve(base_url)
    reset_instance()
    new_flag = solve(base_url)
    assert old_flag != new_flag
