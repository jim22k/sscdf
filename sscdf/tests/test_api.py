import os
import pytest
import sscdf
import graphblas as gb


def test_write_read(tmp_path):
    p1 = tmp_path / "test1.sscdf"
    p1 = str(p1)  # test filename as string behavior
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 2.0, -3., 4.0], nrows=6, ncols=6)
    sscdf.write(p1, g, comment="Created from test_write_read")
    g2 = sscdf.read(p1)
    assert g2.isequal(g)


def test_write_read_noext(tmp_path):
    p1 = tmp_path / "test2"
    assert not os.path.exists(p1.with_suffix('.sscdf'))
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 2.0, -3., 4.0], nrows=6, ncols=6)
    sscdf.write(p1, g, comment="Created from test_write_read_noext")
    assert os.path.exists(p1.with_suffix('.sscdf'))
    assert not os.path.exists(p1)
    g2 = sscdf.read(p1)
    assert g2.isequal(g)


def test_multiwrite_multiread(tmp_path):
    p1 = tmp_path / "test3.sscdf"
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 2.0, -3., 4.0], nrows=6, ncols=6)
    row_degree = g.reduce_rowwise()
    with sscdf.Writer(p1) as w:
        w.write(g, comment="primary object")
        w.write(row_degree, name='row_degree', comment='simply the row degrees')
    with sscdf.Reader(p1) as r:
        g2 = r.read()
        rd2 = r.read('row_degree')
    assert g2.isequal(g)
    assert rd2.isequal(row_degree)


def test_iso(tmp_path):
    p1 = tmp_path / "test4.sscdf"
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 1.0, 1.0, 1.0], nrows=6, ncols=6)
    assert g.ss.is_iso
    with open(p1, 'wb') as w:
        sscdf.write(w, g, comment="Should be iso-valued")
    with open(p1, 'rb') as r:
        info = sscdf.info(r)
        g2 = sscdf.read(p1)
    assert info['iso_value'] == 1.0
    assert g2.isequal(g)


def test_bool(tmp_path):
    p1 = tmp_path / "test5.sscdf"
    g = gb.Matrix.from_values([0, 3], [1, 2], [True, False], nrows=4, ncols=3, dtype=bool)
    assert g.dtype == bool
    sscdf.write(p1, g, comment="Should be bool-valued")
    info = sscdf.info(p1)
    assert info['data_types']['values'] == 'bool'
    g2 = sscdf.read(p1)
    assert g2.isequal(g)


def test_zarr(tmp_path):
    pytest.xfail("netCDF4 nczarr attrs are broken. See https://github.com/Unidata/netcdf4-python/issues/1190")
    # p1 = f'file://{tmp_path / "test6.gbzarr#mode=nczarr,file"}'
    # g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 2.0, -3., 4.0], nrows=6, ncols=6)
    # sscdf.write(p1, g)
    # assert os.path.exists(tmp_path / "test6.gbzarr")
    # g2 = sscdf.read(p1)
    # assert g2.isequal(g)
