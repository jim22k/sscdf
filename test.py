import io
import pytest
import tempfile
import numpy as np
import graphblas as gb
import sscdf


def test_in_memory():
    m = gb.Matrix.from_values(
        [0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 2, 3],
        [1, 2, 3, 4, 5, 6],
        dtype=gb.dtypes.INT8
    )
    f = io.BytesIO()
    sscdf.write(f, m)
    f.seek(0)
    m2 = sscdf.read(f)
    assert m2.isequal(m)


def test_on_disk():
    m = gb.Matrix.from_values(
        [0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 2, 3],
        [1, 2, 3, 4, 5, 6],
        dtype=gb.dtypes.INT8
    )
    with tempfile.NamedTemporaryFile(suffix='.sscdf') as file:
        with open(file.name, 'wb') as f:
            sscdf.write(f, m)
            f.flush()
            m2 = sscdf.read(file.name)
    assert m2.isequal(m)


def test_named_secondary():
    m = gb.Matrix.from_values(
        [0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 2, 3],
        [1, 2, 3, 4, 5, 6],
        dtype=gb.dtypes.INT8
    )
    f = io.BytesIO()
    with sscdf.Writer(f) as w:
        w.write(m)
        w.write(m * 1.2, name='m*1.2')
        w.write(m.reduce_columnwise(), name='colsum')
        w.write(m.reduce_columnwise().dup(dtype=gb.dtypes.BOOL), name='colbool')
    f.seek(0)
    with sscdf.Reader(f) as r:
        m2 = r.read()
        fp = r.read('m*1.2')
        colsum = r.read('colsum')
        colbool = r.read('colbool')
    assert m2.isequal(m)
    assert fp.dtype == 'FP64'
    assert fp.isequal(m * 1.2)
    assert colsum.ss.format == 'full'
    assert (colsum.to_values()[1] == [4, 6, 5, 6]).all()
    assert colbool.dtype == 'BOOL'


def test_info():
    m = gb.Matrix.from_values(
        [0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 2, 3],
        [1, 2, 3, 4, 5, 6],
        dtype=gb.dtypes.INT8
    )
    f = io.BytesIO()
    with sscdf.Writer(f) as w:
        w.write(m, comment="2x4 matrix")
        w.write(m * 1.2, name='m*1.2')
        w.write(m.reduce_columnwise(), name='colsum', comment='sum of the columns')
        w.write(m.reduce_columnwise().dup(dtype=gb.dtypes.BOOL), name='colbool')
    f.seek(0)
    info = sscdf.info(f)
    assert info == {
        'format': 'bitmapr',
        'datatype': 'int8',
        'comment': '2x4 matrix',
        'nrows': 2,
        'ncols': 4,
        'SECONDARY': {
            'm*1.2': {
                'format': 'bitmapr',
                'datatype': 'fp64',
                'nrows': 2,
                'ncols': 4
            },
            'colsum': {
                'format': 'full',
                'datatype': 'int8',
                'size': 4,
                'comment': 'sum of the columns'
            },
            'colbool': {
                'format': 'full',
                'datatype': 'bool',
                'size': 4
            }
        }
    }


def test_scalar_formats():
    s = gb.Scalar('fp64')
    f = io.BytesIO()
    with sscdf.Writer(f) as w:
        w.write(s)  # empty
        s.value = 5.0
        w.write(s, name='notempty')
    f.seek(0)
    with sscdf.Reader(f) as r:
        x = r.read()
        y = r.read('notempty')
    assert x.is_empty
    assert x.dtype == 'fp64'
    assert not y.is_empty
    assert y.value == 5.0


def test_vector_formats():
    v = gb.Vector.from_values(
        [0, 1, 6, 7, 12, 15],
        [1., 2., 3., 4., 5., 6.],
        dtype=gb.dtypes.FP32
    )
    v2 = gb.Vector.from_values(
        [0, 1, 2, 3, 4],
        [-2, -1, 0, 1, 2],
        dtype=gb.dtypes.INT32
    )
    f = io.BytesIO()
    with sscdf.Writer(f) as w:
        w.write(v, name='sparse', format='sparse')
        w.write(v, name='bitmap', format='bitmap')
        w.write(v2, name='full', format='full')
    f.seek(0)
    with sscdf.Reader(f) as r:
        vsparse = r.read('sparse')
        vbitmap = r.read('bitmap')
        vfull = r.read('full')
    assert vsparse.ss.format == 'sparse'
    assert vsparse.isequal(v)
    assert vbitmap.ss.format == 'bitmap'
    assert vbitmap.isequal(v)
    assert vfull.ss.format == 'full'
    assert vfull.isequal(v2)


def test_matrix_formats():
    m = gb.Matrix.from_values(
        [0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 2, 3],
        [1., 2., 3., 4., 5., 6.5],
        dtype=gb.dtypes.FP32
    )
    m2 = gb.Matrix.from_values(
        [0, 0, 0, 0, 1, 1, 1, 1],
        [0, 1, 2, 3, 0, 1, 2, 3],
        [1, 1, 0, 0, 0, 0, 1, 1],
        dtype=gb.dtypes.BOOL
    )
    f = io.BytesIO()
    with sscdf.Writer(f) as w:
        for orientation in ('r', 'c'):
            for fmt in ('cs', 'bitmap', 'coo', 'hypercs'):
                w.write(m, name=f"{fmt}{orientation}", format=f"{fmt}{orientation}")
            w.write(m2, name=f"full{orientation}", format=f"full{orientation}")
    f.seek(0)
    with sscdf.Reader(f) as r:
        for orientation in ('r', 'c'):
            for fmt in ('cs', 'bitmap', 'coo', 'hypercs'):
                x = r.read(name=f"{fmt}{orientation}")
                info = r.info(name=f"{fmt}{orientation}")
                assert info['format'] == f"{fmt}{orientation}"
                if fmt != 'coo':  # coo is not a "real" underlying format in SuiteSparse:GraphBLAS
                    assert x.ss.format == f"{fmt}{orientation}"
                assert x.isequal(m)
            y = r.read(f"full{orientation}")
            assert y.ss.format == f"full{orientation}"
            assert y.isequal(m2)


def test_iso():
    m = gb.Matrix.from_values(
        [0, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 2, 3],
        [2, 2, 2, 2, 2, 2],
        dtype=gb.dtypes.INT8
    )
    assert m.ss.is_iso
    f = io.BytesIO()
    sscdf.write(f, m)
    f.seek(0)
    with sscdf.Reader(f) as r:
        assert len(r.ds.variables["values"].dimensions) == 0
        m2 = r.read()
    assert m2.isequal(m)


def test_empty():
    m = gb.Matrix.from_values([], [], [], dtype=gb.dtypes.INT8, nrows=5, ncols=7)
    assert m.nvals == 0
    f = io.BytesIO()
    with sscdf.Writer(f) as w:
        w.write(m)
        w.write(m.reduce_columnwise(), name='colsum')
    f.seek(0)
    with sscdf.Reader(f) as r:
        m2 = r.read()
        colsum = r.read('colsum')
    assert m2.nvals == 0
    assert m2.isequal(m)
    assert colsum.nvals == 0
    assert colsum.size == m.ncols
