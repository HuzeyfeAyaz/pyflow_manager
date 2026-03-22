#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pyflow_manager.loader import _process_parameter_value

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