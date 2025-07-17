import os
import subprocess
import pytest
import tempfile

def clean_outputs():
    for f in os.listdir('.'):
        if f.startswith('output') or f.startswith('sweep_'):
            os.remove(f)

def test_print_dag_ascii():
    result = subprocess.run([
        'python', '-m', 'pyflow_manager.cli', 'tests/sample_tasks.yaml', '--print-dag'
    ], capture_output=True, text=True)
    assert 'task1' in result.stdout
    assert 'sweep_task_a1_bx' in result.stdout
    assert result.returncode == 0

def test_run_specific_task():
    clean_outputs()
    result = subprocess.run([
        'python', '-m', 'pyflow_manager.cli', 'tests/sample_tasks.yaml', '-t', 'sweep_task_a1_bx'
    ], capture_output=True, text=True)
    assert os.path.exists('sweep_1_x.txt')
    # Only this output should exist
    for f in ['sweep_1_y.txt', 'sweep_2_x.txt', 'sweep_2_y.txt']:
        assert not os.path.exists(f)
    assert result.returncode == 0

def test_include_import():
    clean_outputs()
    import sys
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # task3 is in included_tasks.yaml, depends on task2
    subprocess.run([
        'python', '-m', 'pyflow_manager.cli', 'tests/sample_tasks.yaml', '-t', 'task3'
    ], check=True, env=env)
    print('Files in ./:', os.listdir('.'))
    assert os.path.exists('output3.txt')

def test_cyclic_include_error(tmp_path):
    # Create two files that include each other
    file1 = tmp_path / 'file1.yaml'
    file2 = tmp_path / 'file2.yaml'
    file1.write_text('include: [file2.yaml]\ntasks: {a: {command: echo, inputs: [], outputs: [a.txt]}}')
    file2.write_text('include: [file1.yaml]\ntasks: {b: {command: echo, inputs: [], outputs: [b.txt]}}')
    result = subprocess.run([
        'python', '-m', 'pyflow_manager.cli', str(file1)
    ], capture_output=True, text=True)
    assert 'Cyclic or duplicate include' in result.stderr or 'Cyclic or duplicate include' in result.stdout
    assert result.returncode != 0

def test_duplicate_task_error(tmp_path):
    # Create two files with the same task name and include one in the other
    file1 = tmp_path / 'dup1.yaml'
    file2 = tmp_path / 'dup2.yaml'
    file1.write_text('tasks: {a: {command: echo, inputs: [], outputs: [a.txt]}}')
    file2.write_text(f'include: [dup1.yaml]\ntasks: {{a: {{command: echo, inputs: [], outputs: [b.txt]}}}}')
    result = subprocess.run([
        'python', '-m', 'pyflow_manager.cli', str(file2)
    ], capture_output=True, text=True)
    assert 'Duplicate task name' in result.stderr or 'Duplicate task name' in result.stdout
    assert result.returncode != 0

def test_missing_dependency_error(tmp_path):
    # Create a file with a missing dependency
    file1 = tmp_path / 'missingdep.yaml'
    file1.write_text('tasks: {a: {command: echo, inputs: [b.outputs], outputs: [a.txt]}}')
    result = subprocess.run([
        'python', '-m', 'pyflow_manager.cli', str(file1)
    ], capture_output=True, text=True)
    assert 'references unknown task' in result.stderr or 'references unknown task' in result.stdout
    assert result.returncode != 0

def test_visualize_dag():
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        result = subprocess.run([
            'python', '-m', 'pyflow_manager.cli', 'tests/sample_tasks.yaml', 
            '--visualize-dag', '--output-image', output_path
        ], capture_output=True, text=True)
        
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0  # File should have content
        assert f"DAG visualization saved to: {output_path}" in result.stdout
        assert result.returncode == 0
    finally:
        # Clean up the temporary file
        if os.path.exists(output_path):
            os.remove(output_path) 