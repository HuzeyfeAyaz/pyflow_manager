import os
import pytest
from pyflow_manager.pyflow_manager import PyflowManager

OUTPUT_FILES = [
    'output1.txt', 'output2.txt', 'output3.txt', 'output4.txt', 'output5.txt',
    'output6.txt', 'output7.txt', 'output8.txt', 'output9.txt', 'output10.txt',
    'output11.txt', 'output12.txt', 'output13.txt'
]

SWEEP_OUTPUTS = [
    'sweep_1_x.txt', 'sweep_1_y.txt', 'sweep_2_x.txt', 'sweep_2_y.txt'
]

def clean_outputs():
    for f in OUTPUT_FILES + SWEEP_OUTPUTS:
        if os.path.exists(f):
            os.remove(f)

def test_pyflow_manager():
    clean_outputs()
    # Create a PyflowManager instance with the sample YAML file
    yaml_file = os.path.join(os.path.dirname(__file__), 'sample_tasks.yaml')
    manager = PyflowManager(yaml_file, 2)

    # Execute the pyflow
    manager.execute_workflow()

    # All outputs except those that should not exist due to intentional failures
    for output in [
        'output1.txt', 'output2.txt', 'output3.txt', 'output4.txt', 'output5.txt',
        'output6.txt', 'output9.txt', 'output10.txt', 'output11.txt', 'output12.txt']:
        assert os.path.exists(output), f"{output} should exist after workflow execution"
    for sweep_out in SWEEP_OUTPUTS:
        assert os.path.exists(sweep_out), f"{sweep_out} should be created by parameter sweep"
    # These outputs should not exist due to failed dependencies
    for output in ['output7.txt', 'output8.txt', 'output13.txt']:
        assert not os.path.exists(output), f"{output} should not exist due to failed dependencies"

    # Test the skip_existing flag
    output_files = ['output1.txt', 'output5.txt']

    # Record the initial modification times
    initial_mod_times = {
        output_file: os.path.getmtime(output_file)
        for output_file in output_files}

    # Execute the workflow again
    manager.execute_workflow()

    # Check if the files are skipped and not re-created or modified
    for output_file in output_files:
        assert os.path.exists(output_file), f"{output_file} should exist"
        assert os.path.getmtime(
            output_file) == initial_mod_times[output_file], f"{output_file} should not be modified"


def test_pyflow_manager_with_output_references():
    clean_outputs()
    """
    This test verifies that the workflow manager correctly resolves inputs specified as 'taskX.outputs'.
    The sample_tasks.yaml now uses this referencing style for some tasks.
    """
    yaml_file = os.path.join(os.path.dirname(__file__), 'sample_tasks.yaml')
    manager = PyflowManager(yaml_file, 2)
    manager.execute_workflow()
    for output in [
        'output1.txt', 'output2.txt', 'output3.txt', 'output4.txt', 'output5.txt',
        'output6.txt', 'output9.txt', 'output10.txt', 'output11.txt', 'output12.txt']:
        assert os.path.exists(output), f"{output} should exist after workflow execution"
    for sweep_out in SWEEP_OUTPUTS:
        assert os.path.exists(sweep_out), f"{sweep_out} should be created by parameter sweep"
    for output in ['output7.txt', 'output8.txt', 'output13.txt']:
        assert not os.path.exists(output), f"{output} should not exist due to failed dependencies"

if __name__ == "__main__":
    pytest.main()
