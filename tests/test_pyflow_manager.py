import os
import pytest
from pyflow_manager.pyflow_manager import PyflowManager


def test_pyflow_manager():
    # Create a PyflowManager instance with the sample YAML file
    yaml_file = os.path.join(os.path.dirname(__file__), 'sample_tasks.yaml')
    manager = PyflowManager(yaml_file, 2)

    # Execute the pyflow
    manager.execute_workflow()

    # Check if the output files were created
    assert os.path.exists('output1.txt')
    assert os.path.exists('output2.txt')
    assert os.path.exists('output3.txt')
    assert os.path.exists('output4.txt')
    assert os.path.exists('output5.txt')
    assert not os.path.exists('output6.txt')
    assert not os.path.exists('output7.txt')

    # Test the skip_existing flag
    output_files = ['output1.txt', 'output2.txt']

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


if __name__ == "__main__":
    pytest.main()
