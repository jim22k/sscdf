# sscdf Specification Document
sscdf is a specific mapping of binary arrays and metadata, stored in netCDF 4,
which represents all of the possible in-memory formats used by SuiteSparse::GraphBLAS.

While the primary purpose is to allow for easy serialization and deserialization of objects
by SuiteSparse library users, it is also general enough that users of other graph libraries
can easily decode and ingest these same sparse Matrices, Vectors, and Scalars.

While being informed by SuiteSparse::GraphBLAS, the goal is to become a standard interchange
format for all sparse tensors.

### netCDF
The underlying file format is [netCDF](https://www.unidata.ucar.edu/software/netcdf/), which is a widely used and adopted format for storing n-dimensional numeric data.
Version 4 utilizes the HDF5 storage format to allows groups of related arrays to be stored together.

While sscdf does not need the full set of options provided by netCDF, using an established and
hardened library and specification makes it easier for many programming languages to
quickly extract the binary arrays needed to reconstitute the SuiteSparse storage formats.

### Version
This is version 1.0 of the specification.

At the top level of the netCDF file, an attribute named "version" shall contain the string "1.0".
Any sscdf file not containing this version attribute or containing a version other than "1.0" is not valid.

### Compression
Compression is allowed in netCDF 4 (it comes along with HDF5 format). Dense arrays may be stored compressed
in the netCDF Variables, but this is not required.

## Storing One or More GraphBLAS Objects

### Primary Storage
Each sscdf file has room for exactly one primary object to be stored. This object is not designated
with a name in the file, but is assumed to be described by the filename or some other
mechanism outside of the netCDF file.

All metadata and numeric data for the primary object are stored at the root level of the
netCDF file.

### Named Secondary Storage
Additional secondary objects may be stored together with the primary object in the same sscdf file.
Each secondary object must be given a unique name. All metadata and numeric data associated with the
secondary object are stored in a Group, which is a construct provided by netCDF 4 utilizing the HDF5
structure.

Only one level of group nesting is supported, with the group name matching the name of the secondary
object.

The storage scheme for a single object, whether primary or secondary, is identical. The only difference
is where those items are stored (at the root level or in a named group).

Typically, the usage of secondary objects is to hold alternate formats of the primary object. For example,
if the primary object is a matrix, the transpose might be saved as a secondary format. The maximum, minimum,
or mean value might also be saved as a secondary object. These types of pre-computed statistics are
often helpful for algorithms, and saving them avoids the need to recompute them later.

While this is the typical usage, no restriction is placed on secondary objects other than that they
each be described by a unique name.

## Details of Storing a Single Object

### Metadata
Each stored object contains up to 3 pieces of metadata.
These are stored as netCDF attributes of type string.

- format (mandatory)
- datatype (mandatory)
- comment (optional)

The format is used to determine the whether the object is a Matrix, Vector, or Scalar, as formats
are unique across all ranks of tensors. The format also determines what named arrays
must exist.

The dtype represents the GraphBLAS datatype and is usually a redundant piece of information, given that netCDF arrays contain
their dtype. However, GraphBLAS bool type does not have an equivalent data type in netCDF, so
this attribute allows for proper roundtripping of GraphBLAS objects of all data types.

The comment is optional and is not used when reconstituting the GraphBLAS object. It is purely
for the use of describing the data to human users.

### Arrays
The various SuiteSparse::GraphBLAS formats describe sparse objects using different combinations of dense arrays.
These dense arrays are stored as netCDF Variables linked to a single Dimension.
Each Dimension is used by exactly one Variable, making them independent 1-D arrays.
The Dimensions are always sized (i.e. Unlimited is not allowed) according to the size of the dense array they will represent.

Each netCDF Variable is given a datatype which must match the mapping below. In general,
there is a 1:1 mapping from GraphBLAS datatypes to netCDF datatypes, with the exception of "bool".

### Scalars
Scalars are also stored as netCDF Variables, but are not linked to a Dimension.

Scalars have a datatype, just like arrays.

### Datatypes
This is the mapping between GraphBLAS datatypes to netCDF datatypes.

|GraphBLAS|netCDF|
|---------|------|
|bool     |i1    |
|int8     |i1    |
|int16    |i2    |
|int32    |i4    |
|int64    |i8    |
|uint8    |u1    |
|uint16   |u2    |
|uint32   |u4    |
|uint64   |u8    |
|fp32     |f4    |
|fp64     |f8    |

### GraphBLAS Matrix Representations
A matrix has two shape dimensions, stored as u8 Scalars:
- nrows
- ncols

These represent the overall dimensions of the sparse matrix.

There are 10 available formats for storing matrices:
- **csr** : *compressed sparse row*
- **csc** : *compressed sparse column*
- **hypercsr** : *hypersparse CSR*)
- **hypercsc** : *hypersparse CSC*)
- **bitmapr** : *row-oriented bitmap*)
- **bitmapc** : *column-oriented bitmap*)
- **fullr** : *row-oriented dense*)
- **fullc** : *column-oriented dense*)
- **coor** : *coordinate format in row-sorted order*)
- **cooc** : *coordinate format in column-sorted order*)

Each format has a row-wise and column-wise orientation which affects the ability to easily iterate over the values in that direction.

The following table details the expected array names and datatypes for each format.

| Format |Array Name|Datatype|Size|
|--------|----------|--------|----|
|csr     |indptr<br>col_indices<br>values|u8<br>u8<br>(any)|nrows+1<br>nvals<br>nvals|
|csc     |indptr<br>row_indices<br>values|u8<br>u8<br>(any)|ncols+1<br>nvals<br>nvals|
|hypercsr|indptr<br>rows<br>col_indices<br>values|u8<br>u8<br>u8<br>(any)|nonempty_rows+1<br>nonempty_rows<br>nvals<br>nvals|
|hypercsc|indptr<br>cols<br>row_indices<br>values|u8<br>u8<br>u8<br>(any)|nonempty_cols+1<br>nonempty_cols<br>nvals<br>nvals|
|bitmapr |bitmap<br>values|i1<br>(any)|nrows * ncols<br>nrows * ncols|
|bitmapc |bitmap<br>values|i1<br>(any)|nrows * ncols<br>nrows * ncols|
|fullr   |values|(any)|nrows * ncols|
|fullc   |values|(any)|nrows * ncols|
|coor    |rows<br>cols<br>values|u8<br>u8<br>(any)|nvals<br>nvals<br>nvals|
|cooc    |rows<br>cols<br>values|u8<br>u8<br>(any)|nvals<br>nvals<br>nvals|

Note that 2-D bitmap and full arrays are stored as flattened 1-D arrays.

### GraphBLAS Vector Representations
A vector has one shape dimension, stored as a u8 Scalar:
- size

This represents the overall size of the sparse vector, not the number of non-empty values.

There are 3 available formats for storing vectors:
- **sparse**
- **bitmap**
- **full**

The following table details the expected array names and datatypes for each format.

|Format|Array Name|Datatype|Size|
|------|----------|--------|----|
|sparse|indices<br>values|u8<br>(any)|nvals<br>nvals|
|bitmap|bitmap<br>values|i1<br>(any)|size<br>size|
|full  |values|(any)|size|

### GraphBLAS Scalar Representations
A scalar has no shape dimensions to store.

There are 2 available formats for storing scalars:
- **scalar**
- **scalar_empty**

The following table details the expected Scalar names.

|Format|Scalar name|Datatype|
|------|-----------|--------|
|scalar|value|(any)|
|scalar_empty| | |

Note: The "datatype" metadata will be used for scalar_empty to reconstitute an empty scalar
of the correct GraphBLAS datatype.

### Iso-Valued Objects
A special kind of Matrix and Vector exists where all non-empty values are identical. These
iso-valued objects are handled in an efficient format. Rather than duplicating the single value,
it is stored as a single value.

All formats use the name "values" for the array of values. When the object is iso-valued, the
"values" is stored as a Scalar rather than as an Array. When reading the sscdf format,
the "values" must be checked to see if it is associated with a Dimension. If it is not, it means
the object is iso-valued.
