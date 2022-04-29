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
    w.write(my_matrix.reduce_scalar(), name="total_sum")
```

## Multiple Object Loading
When a sscdf file contains multiple objects, the easiest way to access the named
objects is using a `Reader` in a `with` block.

```python
with sscdf.Reader(filename) as r:
    my_matrix = r.read()
    row_degrees = r.read('row_degrees')
    total = r.read('total_sum')
```

## Inspecting sscdf Files
To view what objects exist in an sscdf file, use the `info()` method.
This will show the metadata and attributes of the primary as well as any
secondary objects in the file.

```python
>>> sscdf.info(filename)
{'format': 'csr',
 'datatype': 'int64',
 'comment': 'Data came from the internet',
 'nrows': 4,
 'ncols': 4,
 'SECONDARY': {
     'row_degrees': {
         'format': 'full',
         'datatype': 'int64',
         'size': 4
     },
     'total_sum': {
         'format': 'scalar',
         'datatype': 'int64'
     }
 }
}
```
