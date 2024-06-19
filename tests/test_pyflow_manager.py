import os
import pytest
from pyflow_manager.pyflow_manager import PyflowManager


def test_pyflow_manager():
    # Create a PyflowManager instance with the sample YAML file
    yaml_file = os.path.join(os.path.dirname(__file__), 'sample_tasks.yaml')
    manager = PyflowManager(yaml_file)

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


if __name__ == "__main__":
    pytest.main()
