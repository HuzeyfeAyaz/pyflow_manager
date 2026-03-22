#!/usr/bin/env python3

import re

def _process_parameter_value(value):
    """
    Process a parameter value, executing Python code in triple backticks if present.
    
    Args:
        value: The parameter value to process
        
    Returns:
        The processed value, with Python code in triple backticks executed
    """
    if isinstance(value, str):
        # Check if the value is Python code in triple backticks
        triple_backtick_pattern = r"^```(.*)```$"
        match = re.match(triple_backtick_pattern, value.strip())
        if match:
            # Execute the Python code
            python_code = match.group(1)
            try:
                # Use eval to execute the Python code
                return eval(python_code)
            except Exception as e:
                raise ValueError(f"Error executing Python code '{python_code}': {e}")
    
    # Return the value as-is if it's not a string with triple backticks
    return value

if __name__ == "__main__":
    # Test the parameter processing function
    test_value = '```list(range(3))```'
    print(f"Testing with value: {test_value}")
    processed_value = _process_parameter_value(test_value)
    print(f"Processed value: {processed_value}")
    print(f"Type: {type(processed_value)}")
    
    # Test with a simple value
    simple_value = 'simple_string'
    print(f"\nTesting with simple value: {simple_value}")
    processed_simple = _process_parameter_value(simple_value)
    print(f"Processed simple value: {processed_simple}")