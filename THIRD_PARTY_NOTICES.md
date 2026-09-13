# Third-party notices

The add-in source in this repository is MIT-licensed; see [LICENSE](LICENSE).

## Bundled binary inventory

The current Windows bundle contains `stl2step 1.4.3`, OCCT `8.0.1`,
FreeType `2.14.3`, libpng `1.6.58`, zlib `1.3.2`, and Microsoft Visual C++
runtime DLLs `14.44.35211.0`. The Brotli and bzip2 DLLs do not expose a
reliable version in their Windows file metadata; their exact source versions
should be recorded from the upstream release manifest when available.

| Files | Component | License / obligation |
| --- | --- | --- |
| `stl2step.exe` | [stl2step](https://github.com/BlinkingSun/stl2step) 1.4.3 | MIT |
| `TK*.dll`, `TKernel.dll` | [OCCT](https://dev.opencascade.org/resources/licensing) 8.0.1 | LGPL-2.1 with Open CASCADE Exception; provide license and corresponding source access |
| `brotlicommon.dll`, `brotlidec.dll` | [Brotli](https://github.com/google/brotli) | MIT; retain copyright and license notice |
| `bz2.dll` | [bzip2/libbzip2](https://sourceware.org/bzip2/) | bzip2 license; retain copyright and conditions |
| `freetype.dll` | [FreeType](https://freetype.org/license.html) 2.14.3 | FreeType License; retain its credit/license notice |
| `libpng16.dll` | [libpng](https://www.libpng.org/pub/png/libpng.html) 1.6.58 | libpng license and notices |
| `z.dll` | [zlib](https://zlib.net/) 1.3.2 | zlib license and notices |
| `msvcp140.dll`, `vcruntime140*.dll` | Microsoft Visual C++ Redistributable 14.44.35211.0 | Redistributable under Microsoft’s applicable terms; confirm the release asset includes the required notice |

The version numbers above were read from the release-vendored binaries. A
future engine update must refresh this table and its license files if the
dependency set or versions change.

## stl2step

The bundled `stl2step.exe` is from the upstream
[stl2step project](https://github.com/BlinkingSun/stl2step), which is released
under the MIT License. Its license text is included in the upstream repository.

## Open CASCADE Technology (OCCT)

The bundled engine is built with Open CASCADE Technology. OCCT is licensed
under the GNU Lesser General Public License version 2.1 with the Open CASCADE
Exception. See the [official OCCT licensing page](https://dev.opencascade.org/resources/licensing)
and [license text](https://occt3d.com/dev/doc/overview/html/occt_public_license.html).

The stl2step source and build instructions are available from the
[upstream stl2step project](https://github.com/BlinkingSun/stl2step). The
corresponding OCCT source is available from the official OCCT distribution.
For a published binary release, include the exact OCCT version and applicable
license texts or a compliant written source offer with the release artifact.

The linked project pages are the authoritative locations for the full license
texts. Before publishing a release, copy the applicable license texts into the
release artifact or provide a stable written source offer for the LGPL-covered
OCCT components, and confirm the Microsoft runtime redistribution terms.

