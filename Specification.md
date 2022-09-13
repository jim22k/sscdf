# sscdf Specification Document
sscdf is a specific mapping of binary arrays and metadata, stored in netCDF 4,
which represents v1 of the [binsparse storage format](https://github.com/GraphBLAS/binsparse-specification).

### netCDF
The underlying file format is [netCDF](https://www.unidata.ucar.edu/software/netcdf/),
which is a widely used and adopted format for storing n-dimensional numeric data.
Version 4 utilizes the HDF5 storage format to allows groups of related arrays to be stored together.

While sscdf does not need the full set of options provided by netCDF, using an established and
hardened library and specification makes it easier for many programming languages to
quickly extract the binary arrays needed to reconstitute the SuiteSparse storage formats.

### Version
This implements version 1.0 of the binsparse specification.

At the top level of the netCDF file, an attribute named "version" shall contain the string "1.0".
Any sscdf file not containing this version attribute or containing a version other than "1.0" is not valid.

### Compression
While compression is allowed in netCDF 4 (it comes along with HDF5 format), everything will be stored
uncompressed to allow better compatibility.

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
Each stored object contains a metadata attribute, which stores a string parseable as JSON.
Within the JSON are the following keys:

- format (mandatory)
- shape (mandatory)
- data_types (mandatory)
- iso_value (optional)
- comment (optional)

The format is used to determine the whether the object is a Matrix or Vector as well as
the layout. The layout uniquely determines what named arrays must exist.

The shape must be a list of integers representing the shape of the Matrix or Vector.

The data_types is a map of each named array to its datatype and is usually a redundant piece
of information, given that netCDF arrays contain their datatype. However, not all available
datatypes have a corresponding datatype in netCDF4, so these are explicitly stated for the
purpose of proper round-tripping.

If the Matrix or Vector is iso-valued, the single value is listed as `iso_value` and no
`values` array is defined. The value should be a JSON int or float or bool. The actual
datatype will be deciphered from the datatype entry.

The comment is optional and is not used when reconstituting the GraphBLAS object. It is purely
for the use of describing the data to human users.

### Arrays
The various SuiteSparse::GraphBLAS formats describe sparse objects using different combinations of dense arrays.
These dense arrays are stored as netCDF Variables linked to a single Dimension.
Each Dimension is used by exactly one Variable, making them independent 1-D arrays.
The Dimensions are always sized (i.e. Unlimited is not allowed) according to the size of the dense
array they will represent.

Each netCDF Variable is given a datatype which must match the mapping below. In general,
there is a 1:1 mapping from GraphBLAS datatypes to netCDF datatypes, with the exception of "bool".

### Datatypes
This is the mapping between GraphBLAS datatypes to binsparse datatypes to netCDF datatypes.

|GraphBLAS| BinSparse | netCDF |
|---------|-----------|--------|
|bool     | bool      | i1     |
|int8     | int8      | i1     |
|int16    | int16     | i2     |
|int32    | int32     | i4     |
|int64    | int64     | i8     |
|uint8    | uint8     | u1     |
|uint16   | uint16    | u2     |
|uint32   | uint32    | u4     |
|uint64   | uint64    | u8     |
|fp32     | float32   | f4     |
|fp64     | float64   | f8     |

### GraphBLAS Matrix Representations
The shape of a matrix is [nrows, ncols]

There are 7 available formats for storing matrices:
- **CSR** : *compressed sparse row*
- **CSC** : *compressed sparse column*
- **DCSR** : *double-compressed CSR*
- **DCSC** : *double-compressed CSC*
- **COOR** : *coordinate format in row-sorted order*
- **COOC** : *coordinate format in column-sorted order*
- **COO** : *an alias for COOR*

The following table details the expected array names and datatypes for each format.

| Format | Array Name                                   | Size                                               |
|--------|----------------------------------------------|----------------------------------------------------|
| CSR | pointers_0<br>indices_1<br>values               | nrows+1<br>nvals<br>nvals                          |
| CSC | pointers_0<br>indices_1<br>values               | ncols+1<br>nvals<br>nvals                          |
| DCSR | indices_0<br>pointers_0<br>indices_1<br>values | nonempty_rows<br>nonempty_rows+1<br>nvals<br>nvals |
| DCSC | indices_0<br>pointers_0<br>indices_1<br>values | nonempty_cols<br>nonempty_cols+1<br>nvals<br>nvals |
| COOR | rows<br>cols<br>values                         | nvals<br>nvals<br>nvals                            |
| COOC | rows<br>cols<br>values                         | nvals<br>nvals<br>nvals                            |

### GraphBLAS Vector Representations
The shape of a vector is [size]

Note: The size represents the overall size of the sparse vector, not the number of non-empty values.

There is 1 available format for storing vectors:
- **VEC**

The following table details the expected array names and datatypes for each format.

| Format | Array Name          | Size           |
|--------|---------------------|----------------|
| VEC    | indices_0<br>values | nvals<br>nvals |
