# Comprehensive pytest-compatible test suite for pyflow-manager
import sys
sys.path.append('./pyflow_manager')
from loader import load_tasks
from pyflow_manager import PyflowManager
import pytest

class TestParameterProcessing:
    """Test parameter processing logic"""
    
    def test_command_parameters_only(self):
        """Test task generation with parameters only in command"""
        tasks = load_tasks('tests/test_command_cluster_only.yaml')
        
        # Should generate 3 tasks (one per cluster_id)
        assert len(tasks) == 3
        
        # Check task names follow expected pattern
        task_names = list(tasks.keys())
        expected_patterns = ['task_debug_cluster_id0', 'task_debug_cluster_id1', 'task_debug_cluster_id2']
        for pattern in expected_patterns:
            assert any(pattern in name for name in task_names)
        
        # Check that command parameters are properly substituted
        for task_name, task_details in tasks.items():
            assert 'cluster_id' in task_name
            assert task_details['command']  # Command should exist
            assert '{cluster_id}' not in task_details['command']  # Should be substituted
    
    def test_mixed_parameters(self):
        """Test mixed parameters (some in command, some in outputs)"""
        tasks = load_tasks('tests/test_debug.yaml')
        
        # Should generate 3 tasks (one per cluster_id in command)
        assert len(tasks) == 3
        
        # Check that cluster_id appears in task names but model_id does not
        for task_name in tasks.keys():
            assert 'cluster_id' in task_name
            assert 'model_id' not in task_name
        
        # Check outputs are properly expanded for non-command parameters
        for task_name, task_details in tasks.items():
            outputs = task_details['outputs']
            # Should have outputs for all model_id values (0, 1, 2)
            assert len(outputs) == 3
            for output in outputs:
                assert 'model_' in output
                assert output.endswith('.parquet')

class TestPythonExpressions:
    """Test Python expression processing"""
    
    def test_expressions_in_parameters(self):
        """Test Python expressions in parameter values"""
        tasks = load_tasks('tests/test_python_expressions_everywhere.yaml')
        
        param_task = tasks['test_expressions_in_parameters']
        assert 'parameters' in param_task
        assert param_task['parameters']['value'] == [0, 1]
    
    def test_expressions_in_command(self):
        """Test Python expressions in command"""
        tasks = load_tasks('tests/test_python_expressions_everywhere.yaml')
        
        cmd_task = tasks['test_expressions_in_command']
        expected_cmd = "echo 'Numbers: 0 1 2'"
        assert cmd_task['command'] == expected_cmd
    
    def test_expressions_in_inputs(self):
        """Test Python expressions in inputs"""
        tasks = load_tasks('tests/test_python_expressions_everywhere.yaml')
        
        input_task = tasks['test_expressions_in_inputs']
        expected_inputs = ['input_1.txt', 'input_2.txt']
        assert input_task['inputs'] == expected_inputs
    
    def test_expressions_in_outputs(self):
        """Test Python expressions in outputs"""
        tasks = load_tasks('tests/test_python_expressions_everywhere.yaml')
        
        output_task = tasks['test_expressions_in_outputs']
        expected_outputs = ['output_0.txt', 'output_1.txt']
        assert output_task['outputs'] == expected_outputs

class TestPythonCodeExecution:
    """Test Python code execution in parameters"""
    
    def test_parameter_code_execution(self):
        """Test execution of Python code in parameter definitions"""
        tasks = load_tasks('tests/test_python_code_execution.yaml')
        
        # Should generate 3 tasks (for values 0, 1, 2)
        assert len(tasks) == 3
        
        # Check task names and commands
        for i in range(3):
            task_name = f"test_task_value{i}"
            assert task_name in tasks
            
            task = tasks[task_name]
            expected_cmd = f"echo 'Testing {i}'"
            assert task['command'] == expected_cmd
            
            expected_output = f"output_{i}.txt"
            assert expected_output in task['outputs']

class TestInputOutputDependencies:
    """Test input/output dependency processing"""
    
    def test_simple_dependencies(self):
        """Test simple input/output dependencies"""
        # Create test YAML with dependencies
        dependency_yaml = """tasks:
  task1:
    command: "touch output1.txt"
    outputs: ["output1.txt"]
  
  task2:
    command: "cat input1.txt"
    inputs: ["output1.txt"]
    outputs: ["output2.txt"]
"""
        with open('tests/test_simple_deps.yaml', 'w') as f:
            f.write(dependency_yaml)
        
        tasks = load_tasks('tests/test_simple_deps.yaml')
        assert len(tasks) == 2
        
        # Check dependencies are preserved
        task1 = tasks['task1']
        task2 = tasks['task2']
        
        assert 'output1.txt' in task1['outputs']
        assert 'output1.txt' in task2['inputs']
        assert 'output2.txt' in task2['outputs']
    
    def test_multiple_dependencies(self):
        """Test multiple input dependencies"""
        dependency_yaml = """tasks:
  task1:
    command: "touch output1.txt"
    outputs: ["output1.txt"]
  
  task2:
    command: "touch output2.txt"
    outputs: ["output2.txt"]
  
  task3:
    command: "combine inputs"
    inputs: ["output1.txt", "output2.txt"]
    outputs: ["combined.txt"]
"""
        with open('tests/test_multi_deps.yaml', 'w') as f:
            f.write(dependency_yaml)
        
        tasks = load_tasks('tests/test_multi_deps.yaml')
        assert len(tasks) == 3
        
        task3 = tasks['task3']
        assert len(task3['inputs']) == 2
        assert 'output1.txt' in task3['inputs']
        assert 'output2.txt' in task3['inputs']

class TestDAGCreation:
    """Test DAG creation and dependency resolution"""
    
    def test_dag_creation(self):
        """Test DAG creation from tasks"""
        dependency_yaml = """tasks:
  task1:
    command: "touch output1.txt"
    outputs: ["output1.txt"]
  
  task2:
    command: "cat input1.txt"
    inputs: ["output1.txt"]
    outputs: ["output2.txt"]
  
  task3:
    command: "process input2.txt"
    inputs: ["output1.txt", "output2.txt"]
    outputs: ["final_output.txt"]
"""
        with open('tests/test_dag.yaml', 'w') as f:
            f.write(dependency_yaml)
        
        manager = PyflowManager('tests/test_dag.yaml', 1)
        
        # Check DAG structure
        assert len(manager.tasks) == 3
        assert len(manager.dag.nodes()) == 3
        
        # Check dependencies (task2 and task3 should depend on task1)
        assert 'task1' in manager.dependencies['task2']
        assert 'task1' in manager.dependencies['task3']
        
        # task3 should also depend on task2
        assert 'task2' in manager.dependencies['task3']
    
    def test_dag_execution_filtering(self):
        """Test DAG filtering for execution"""
        manager = PyflowManager('tests/test_dag.yaml', 1, skip_existing=False)
        
        # Should not filter out any tasks when skip_existing is False
        manager.filter_dag_for_execution()
        assert len(manager.tasks) == 3

class TestComplexScenarios:
    """Test complex scenarios with mixed features"""
    
    def test_complex_parameters_and_dependencies(self):
        """Test complex scenario with parameters and dependencies"""
        complex_yaml = """include: "included_basic.yaml"

tasks:
  param_task:
    command: "process cluster {cluster_id}"
    inputs: ["input_cluster_{cluster_id}.txt"]
    outputs: ["output_cluster_{cluster_id}_model_{model_id}.parquet"]
    parameters:
      cluster_id: [0, 1]
      model_id: [10, 20]
"""
        with open('tests/test_complex.yaml', 'w') as f:
            f.write(complex_yaml)
        
        tasks = load_tasks('tests/test_complex.yaml')
        
        # Should have 2 tasks (one per cluster_id)
        assert len(tasks) == 2
        
        # Check basic task from included file
        assert 'basic_task' in tasks
        assert tasks['basic_task']['outputs'] == ['basic_output.txt']
        
        # Check parameterized task
        for task_name in tasks.keys():
            if 'param_task' in task_name:
                assert 'cluster_id' in task_name
                assert 'model_id' not in task_name  # model_id not in command
        
        # Check that outputs are expanded for all model_id values
        param_tasks = {k: v for k, v in tasks.items() if 'param_task' in k}
        for task in param_tasks.values():
            assert len(task['outputs']) == 2  # 2 model_id values
            outputs = task['outputs']
            assert 'model_10.parquet' in outputs
            assert 'model_20.parquet' in outputs

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_parameters(self):
        """Test task with no parameters"""
        tasks = load_tasks('tests/included_basic.yaml')
        assert len(tasks) == 1
        assert 'basic_task' in tasks
    
    def test_python_expression_errors(self):
        """Test error handling for invalid Python expressions"""
        # This should be tested with invalid expressions
        # For now, just ensure the loader doesn't crash on valid expressions
        tasks = load_tasks('tests/test_python_expressions_everywhere.yaml')
        assert len(tasks) == 4  # All expression tasks should load

if __name__ == "__main__":
    pytest.main([__file__, "-v"])