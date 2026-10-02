"""Language-tool adapter boundary; operations will be added in Step 3.

constructor_reader.read_constructor now converts validated source into the
supplied lambda1 expression types. The adapter will use it for Lint/Interpret
without depending on HTTP requests or view rendering.
"""
