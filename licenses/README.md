# License texts for binary releases

The release ZIP must include this directory alongside the add-in. These links
are the canonical sources for the applicable license texts; keep a copy of
each text in the release artifact rather than relying on a user having an
internet connection.

- [stl2step MIT license](https://github.com/BlinkingSun/stl2step/blob/main/LICENSE)
- [OCCT LGPL-2.1 and Open CASCADE Exception](https://github.com/Open-Cascade-SAS/OCCT/blob/master/LICENSE_LGPL_21.txt)
- [Brotli MIT license](https://github.com/google/brotli/blob/master/LICENSE)
- [bzip2 license](https://sourceware.org/bzip2/)
- [FreeType license](https://github.com/freetype/freetype/blob/master/LICENSE.TXT)
- [libpng license](https://github.com/pnggroup/libpng/blob/libpng18/LICENSE.md)
- [zlib license](https://zlib.net/zlib_license.html)
- [Microsoft Visual C++ redistributable terms](https://visualstudio.microsoft.com/license-terms/)

The checked-in binary bundle is an end-user payload, so a release process
should copy the license texts here (or equivalent full texts) into the
downloadable ZIP. The Microsoft runtime files may be redistributed only under
Microsoft's applicable Visual Studio terms; verify the exact redist package
and terms before shipping.
