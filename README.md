# sscdf
Binary sparse storage scheme for SuiteSparse::GraphBLAS utilizing netCDF4

The format specification is found [here](Specification.md).

## Single Object Storage
sscdf contains a convenience method to save a single object.

`write(file, obj, comment=None)`

- `file` can be a filename or a file-like object opened in "write" mode.
- `obj` is the graphblas object (Matrix, Vector, or Scalar)
- `comment` is optional

## Single Object Loading
Loading the primary object can be done with a convenience method.

`read(file)`

- `file` can be a filename or a file-like object opened in "read" mode.

This returns the primary object in the file, reconstituted
as a graphblas object (Matrix, Vector, or Scalar).

## Multiple Object Storage
When writing multiple associated graphblas objects to a single sscdf file,
the preferred method is using a `Writer` in a `with` block.

```python
with sscdf.Writer(filename) as w:
    w.write(my_matrix, comment="Data came from the internet")
    w.write(my_matrix.reduce_rowwise(), name="row_degrees")
```

## Multiple Object Loading
When a sscdf file contains multiple objects, the easiest way to access the named
objects is using a `Reader` in a `with` block.

```python
with sscdf.Reader(filename) as r:
    my_matrix = r.read()
    row_degrees = r.read('row_degrees')
```

## Inspecting sscdf Files
To view what objects exist in an sscdf file, use the `info()` method.
This will show the metadata and attributes of the primary as well as any
secondary objects in the file.

```python
>>> sscdf.info(filename)
{'version': '1.0',
 'format': 'CSR',
 'shape': [5, 5],
 'data_types': {
     'pointers_0': 'uint64',
     'indices_1': 'uint64',
     'values': 'float32'},
 'comment': 'Data came from the internet',
 'SECONDARY': {
     'row_degrees': {
         'version': '1.0',
         'format': 'VEC',
         'shape': [5],
         'data_types': {
             'indices_0': 'uint64',
             'values': 'float32'},
     }
 }
}
```
